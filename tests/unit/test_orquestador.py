import json
import logging

import pytest

from agentflow.agent.orchestrator import Agente, Conversacion
from agentflow.config import Limites
from agentflow.db.repositories.ventas import ResumenVentas
from agentflow.llm.base import ErrorLLM
from agentflow.observability.logging import FormatoJSON
from agentflow.tools.registry import RegistroHerramientas
from decimal import Decimal
from tests.fakes import HOY, LLMGuionado, RepoFalso, llamada, texto

REPO = lambda: RepoFalso(resumen=ResumenVentas(Decimal("6850.50"), 29, 12))  # noqa: E731


def agente(llm, repo=None, limites=Limites(), reloj=None):
    extra = {"reloj": reloj} if reloj else {}
    return Agente(llm, RegistroHerramientas(repo or REPO()), limites, hoy=lambda: HOY, **extra)


def test_flujo_normal_herramienta_y_respuesta_verificada():
    llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"),
                       texto("Este mes vendimos S/ 6,850.50 en 29 unidades.", tokens_entrada=150, tokens_salida=30)])
    conv = Conversacion()
    r = agente(llm).responder("¿Cuánto vendimos este mes?", conv)
    assert (r.estado, r.origen, r.motivo) == ("ok", "modelo", None)
    assert [h.nombre for h in r.herramientas] == ["ventas_totales"]
    assert (r.tokens_entrada, r.tokens_salida, r.llamadas_llm) == (250, 50, 2)
    assert [m["role"] for m in conv.mensajes] == ["user", "assistant"]
    # el resultado de la herramienta llegó al modelo con el id de la llamada
    tool_msg = llm.llamadas[1]["mensajes"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert json.loads(tool_msg["content"])["ingresos_totales"] == 6850.5


def test_historial_se_envia_en_la_siguiente_pregunta():
    llm = LLMGuionado([texto("Hola, ¿qué quieres saber de ventas?"), texto("De nada.")])
    ag, conv = agente(llm), Conversacion()
    ag.responder("Hola", conv)
    ag.responder("Gracias", conv)
    roles = [m["role"] for m in llm.llamadas[1]["mensajes"]]
    assert roles == ["system", "user", "assistant", "user"]


def test_limite_de_iteraciones_con_modelo_que_nunca_para():
    llm = LLMGuionado(repetir=llamada("ventas_totales", periodo="este_mes"))
    r = agente(llm, limites=Limites(max_iteraciones=4, max_llamadas_herramienta=10)).responder("x", Conversacion())
    assert (r.estado, r.motivo, r.origen) == ("limite", "limite_iteraciones", "plantilla")
    assert r.llamadas_llm == 4 and len(r.herramientas) == 3  # la última vuelta no ejecuta herramientas
    assert llm.llamadas[-1]["tool_choice"] == "none"
    assert "S/ 6,850.50" in r.respuesta  # entrega los datos ya obtenidos


def test_limite_de_llamadas_a_herramientas():
    llm = LLMGuionado(repetir=llamada("ventas_totales", periodo="este_mes"))
    r = agente(llm, limites=Limites(max_iteraciones=10, max_llamadas_herramienta=2)).responder("x", Conversacion())
    assert r.motivo == "limite_herramientas" and len(r.herramientas) == 2


def test_limite_de_tiempo():
    reloj = iter(range(0, 1000, 20))  # cada lectura avanza 20 s
    llm = LLMGuionado(repetir=llamada("ventas_totales", periodo="este_mes"))
    r = agente(llm, limites=Limites(timeout_total_s=30), reloj=lambda: next(reloj)).responder("x", Conversacion())
    assert r.motivo == "tiempo_agotado"


def test_limite_de_tokens():
    pesada = llamada("ventas_totales", periodo="este_mes")
    pesada.tokens_entrada = 5000
    r = agente(LLMGuionado(repetir=pesada), limites=Limites(max_tokens_total=4000)).responder("x", Conversacion())
    assert r.motivo == "limite_tokens" and r.llamadas_llm == 1


def test_cifra_alterada_activa_plantilla_de_respaldo():
    llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"),
                       texto("Vendimos S/ 9,999.00 este mes.")])
    conv = Conversacion()
    r = agente(llm).responder("¿Cuánto vendimos?", conv)
    assert (r.estado, r.motivo, r.origen) == ("degradado", "cifras_no_verificadas", "plantilla")
    assert "9,999" not in r.respuesta and "S/ 6,850.50" in r.respuesta
    assert "9,999" not in conv.mensajes[-1]["content"]  # el historial no guarda la cifra falsa


def test_respuesta_truncada_no_se_muestra_como_completa():
    llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"),
                       texto("Vendimos S/ 6,85", finish_reason="length")])
    r = agente(llm).responder("x", Conversacion())
    assert r.motivo == "respuesta_truncada" and r.origen == "plantilla"
    assert "6,85\n" not in r.respuesta and "S/ 6,850.50" in r.respuesta


def test_herramienta_no_autorizada_se_informa_al_modelo_y_no_ejecuta_nada():
    repo = REPO()
    llm = LLMGuionado([llamada("ejecutar_sql", sql="DROP TABLE ventas"), texto("No puedo hacer eso.")])
    r = agente(llm, repo).responder("borra todo", Conversacion())
    assert repo.llamadas == [] and r.herramientas[0].codigo_error == "herramienta_no_autorizada"
    assert json.loads(llm.llamadas[1]["mensajes"][-1]["content"]) == {"error": "herramienta_no_autorizada"}


def test_argumentos_invalidos_permiten_que_el_modelo_corrija():
    llm = LLMGuionado([llamada("ventas_totales", periodo="ayer"),
                       llamada("ventas_totales", _id="c2", periodo="ultimos_7_dias"),
                       texto("En los últimos 7 días: S/ 6,850.50.")])
    r = agente(llm).responder("x", Conversacion())
    assert [h.ok for h in r.herramientas] == [False, True] and r.estado == "ok"


def test_fallo_del_proveedor_no_expone_detalles_ni_ensucia_el_historial():
    conv = Conversacion()
    r = agente(LLMGuionado([ErrorLLM("limite_tasa", "429 detalle interno")])).responder("x", conv)
    assert r.estado == "error" and r.origen == "mensaje_error" and "429" not in r.respuesta
    assert conv.mensajes == []


def test_respuesta_vacia_se_degrada():
    r = agente(LLMGuionado([texto("   ")])).responder("x", Conversacion())
    assert r.motivo == "respuesta_vacia" and r.estado == "limite"


def test_logs_sin_pregunta_ni_claves():
    manejador = logging.Handler()
    lineas = []
    manejador.emit = lambda rec: lineas.append(FormatoJSON().format(rec))
    log = logging.getLogger("agentflow")
    log.addHandler(manejador), log.setLevel(logging.INFO)
    try:
        llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"), texto("S/ 6,850.50")])
        agente(llm).responder("pregunta CONFIDENCIAL con api_key=abc123", Conversacion())
    finally:
        log.removeHandler(manejador)
    todo = "\n".join(lineas)
    eventos = [json.loads(l)["evento"] for l in lineas]
    assert eventos == ["solicitud", "llm_llamada", "herramienta", "llm_llamada", "respuesta"]
    assert "CONFIDENCIAL" not in todo and "abc123" not in todo
    final = json.loads(lineas[-1])
    assert {"estado", "tokens_entrada", "tokens_salida", "duracion_ms"} <= final.keys()
