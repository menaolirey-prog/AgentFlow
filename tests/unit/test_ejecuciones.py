import json
import logging
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb

from agentflow.agent.orchestrator import Agente, Conversacion
from agentflow.cli import formatear_ejecuciones
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.llm.base import ErrorLLM
from agentflow.observability.logging import FormatoJSON
from agentflow.tools.registry import RegistroHerramientas
from tests.fakes import HOY, AlmacenEnMemoria, EjecucionesFalso, LLMGuionado, RepoFalso, llamada, texto

ID = str(uuid4())
HERR = {"nombre": "ventas_totales", "argumentos": {"periodo": "este_mes"}, "ok": True,
        "codigo_error": None, "duracion_ms": 12}


def _repo(rowcount=1):
    conexion = MagicMock()
    conexion.__enter__.return_value = conexion
    conexion.execute.return_value.rowcount = rowcount
    cursor = conexion.cursor.return_value.__enter__.return_value
    return RegistroEjecuciones(lambda: conexion), conexion, cursor


# ---- repositorio SQL (mocks) ----
def test_iniciar_inserta_en_curso_con_parametros_y_devuelve_id():
    repo, conexion, _ = _repo()
    conexion.execute.return_value.fetchone.return_value = (ID,)
    assert repo.iniciar("sesion-1", 42) == ID
    sql, params = conexion.execute.call_args.args
    assert "INSERT INTO ejecuciones" in sql and params == ("sesion-1", 42)


def test_finalizar_actualiza_solo_si_sigue_en_curso_y_guarda_herramientas():
    repo, conexion, cursor = _repo()
    repo.finalizar(ID, "ok", None, "modelo", 150, 30, 2, 800, [HERR, {**HERR, "nombre": "x" * 200}])
    sql, params = conexion.execute.call_args.args
    assert "estado = 'en_curso'" in sql and params[-1] == ID and params[:3] == ("ok", None, "modelo")
    filas = cursor.executemany.call_args.args[1]
    assert [f[1] for f in filas] == [1, 2]                      # orden
    assert isinstance(filas[0][3], Jsonb)                        # argumentos como jsonb parametrizado
    assert len(filas[1][2]) == 60                                # nombre acotado al CHECK


def test_finalizar_sin_herramientas_no_inserta_filas():
    repo, _, cursor = _repo()
    repo.finalizar(ID, "error", "limite_tasa", "mensaje_error", 0, 0, 0, 5, [])
    cursor.executemany.assert_not_called()


def test_argumentos_rechazados_se_guardan_como_null():
    repo, _, cursor = _repo()
    repo.finalizar(ID, "ok", None, "modelo", 1, 1, 1, 1,
                   [{**HERR, "nombre": "ejecutar_sql", "argumentos": None, "ok": False,
                     "codigo_error": "herramienta_no_autorizada"}])
    assert cursor.executemany.call_args.args[1][0][3] is None   # nunca el JSON crudo del modelo


def test_finalizar_ejecucion_inexistente_o_cerrada_falla_sin_insertar():
    repo, _, cursor = _repo(rowcount=0)
    with pytest.raises(LookupError):
        repo.finalizar(ID, "ok", None, "modelo", 1, 1, 1, 1, [HERR])
    cursor.executemany.assert_not_called()


@pytest.mark.parametrize("estado,origen", [("en_curso", "modelo"), ("hecho", "modelo"), ("ok", "otro")])
def test_finalizar_valida_estado_y_origen_antes_de_tocar_la_base(estado, origen):
    repo, conexion, _ = _repo()
    with pytest.raises(ValueError):
        repo.finalizar(ID, estado, None, origen, 0, 0, 0, 0, [])
    conexion.execute.assert_not_called()


def test_listar_filtra_por_sesion_con_parametros():
    repo, conexion, _ = _repo()
    ahora = datetime(2026, 11, 10, 16, 0)
    conexion.execute.return_value.fetchall.return_value = [(ID, "ok", None, "modelo", 180, 900, ahora, 2)]
    filas = repo.listar("sesion-1", 5)
    assert conexion.execute.call_args.args[1] == ("sesion-1", "sesion-1", 5)
    assert filas[0]["tokens"] == 180 and filas[0]["herramientas"] == 2
    assert "ok" in formatear_ejecuciones(filas) and "2 herr." in formatear_ejecuciones(filas)
    assert "No hay" in formatear_ejecuciones([])


# ---- integración con el orquestador ----
def _agente(llm, ejecuciones):
    return Agente(llm, RegistroHerramientas(RepoFalso()), hoy=lambda: HOY, ejecuciones=ejecuciones)


def test_ejecucion_registrada_con_sesion_herramientas_y_tokens():
    ej, almacen = EjecucionesFalso(), AlmacenEnMemoria()
    conv = Conversacion.nueva(almacen)
    llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"),
                       texto("Este mes: S/ 1,000.00", tokens_entrada=150, tokens_salida=30)])
    r = _agente(llm, ej).responder("¿Cuánto vendimos este mes?", conv)
    assert r.ejecucion_id == "ejec-1" and ej.iniciadas == [(conv.id, len("¿Cuánto vendimos este mes?"))]
    f = ej.finalizadas[0]
    assert (f["id"], f["estado"], f["origen"], f["t_in"], f["t_out"], f["llamadas"]) == ("ejec-1", "ok", "modelo", 250, 50, 2)
    assert [(h["nombre"], h["argumentos"], h["ok"]) for h in f["herramientas"]] == [
        ("ventas_totales", {"periodo": "este_mes"}, True)]


def test_error_del_proveedor_tambien_se_registra_como_error():
    ej = EjecucionesFalso()
    _agente(LLMGuionado([ErrorLLM("limite_tasa", "429")]), ej).responder("x", Conversacion())
    assert ej.finalizadas[0]["estado"] == "error" and ej.finalizadas[0]["motivo"] == "limite_tasa"


def test_herramienta_no_autorizada_se_registra_sin_argumentos_crudos():
    ej = EjecucionesFalso()
    llm = LLMGuionado([llamada("ejecutar_sql", sql="DROP TABLE ventas"), texto("No puedo.")])
    _agente(llm, ej).responder("x", Conversacion())
    h = ej.finalizadas[0]["herramientas"][0]
    assert h["argumentos"] is None and h["codigo_error"] == "herramienta_no_autorizada"
    assert "DROP" not in json.dumps(ej.finalizadas[0])


def test_falla_al_iniciar_no_impide_responder_ni_filtra_detalles(caplog):
    ej = EjecucionesFalso(falla_iniciar=True)
    with caplog.at_level(logging.INFO, logger="agentflow"):
        r = _agente(LLMGuionado([texto("Hola.")]), ej).responder("x", Conversacion())
    assert r.estado == "ok" and r.ejecucion_id is None and ej.finalizadas == []
    evento = next(rec for rec in caplog.records if rec.getMessage() == "error_ejecuciones")
    assert evento.campos == {"fase": "iniciar", "tipo": "RuntimeError"}   # sin el mensaje (traía credenciales)


def test_falla_al_finalizar_no_impide_responder():
    ej = EjecucionesFalso(falla_finalizar=True)
    r = _agente(LLMGuionado([texto("Hola.")]), ej).responder("x", Conversacion())
    assert r.estado == "ok" and r.respuesta == "Hola."


def test_sin_registro_de_ejecuciones_todo_sigue_funcionando():
    r = _agente(LLMGuionado([texto("Hola.")]), None).responder("x", Conversacion())
    assert r.estado == "ok" and r.ejecucion_id is None


def test_ejecucion_id_va_al_log_sin_texto_de_la_pregunta():
    lineas, manejador = [], logging.Handler()
    manejador.emit = lambda rec: lineas.append(FormatoJSON().format(rec))
    log = logging.getLogger("agentflow")
    log.addHandler(manejador), log.setLevel(logging.INFO)
    try:
        _agente(LLMGuionado([texto("Hola.")]), EjecucionesFalso()).responder("PREGUNTA SECRETA", Conversacion())
    finally:
        log.removeHandler(manejador)
    final = json.loads(lineas[-1])
    assert final["evento"] == "respuesta" and final["ejecucion_id"] == "ejec-1"
    assert "SECRETA" not in "".join(lineas)
