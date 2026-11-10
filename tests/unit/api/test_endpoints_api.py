"""Endpoints de negocio con dobles: sin PostgreSQL, sin Groq, sin red."""
import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agentflow.agent.orchestrator import Agente
from agentflow.api.app import crear_app
from agentflow.api.config import Ajustes
from agentflow.api.errors import DemasiadasSolicitudes, ServicioNoDisponible
from agentflow.api.limites import LimitadorVentana
from agentflow.api.servicios import Servicios
from agentflow.tools.registry import RegistroHerramientas
from tests.fakes import AlmacenEnMemoria, EjecucionesFalso, LLMGuionado, RepoFalso, RepoQueFalla, llamada, texto

CLAVE = "k" * 40
HDR = {"Authorization": f"Bearer {CLAVE}"}


class HistorialDoble(AlmacenEnMemoria):
    def listar(self, limite):
        return [{"id": i, "creada_en": "2026-11-10T10:00:00Z", "mensajes": len(m), "inicio": None}
                for i, m in list(self.datos.items())[:limite]]


class EjecDoble(EjecucionesFalso):
    conocida = ""

    def listar(self, conversacion_id=None, limite=10):
        return [{"id": str(uuid4()), "estado": "ok", "motivo": None, "origen": "modelo", "tokens": 120,
                 "duracion_ms": 800, "iniciada_en": "2026-11-10T10:00:00Z", "herramientas": 1}][:limite]

    def detalle(self, ejecucion_id):
        if ejecucion_id != self.conocida:
            return None
        return {"id": ejecucion_id, "conversacion_id": None, "estado": "ok", "motivo": None, "origen": "modelo",
                "pregunta_chars": 10, "tokens_entrada": 100, "tokens_salida": 20, "llamadas_llm": 1,
                "duracion_ms": 500, "iniciada_en": "2026-11-10T10:00:00Z", "finalizada_en": None,
                "herramientas": [{"orden": 1, "herramienta": "ventas_totales", "argumentos": {"periodo": "este_mes"},
                                  "ok": True, "codigo_error": None, "duracion_ms": 5}]}


def _montar(llm=None, repo=None, **ajustes):
    historial, ejec = HistorialDoble(), EjecDoble()
    ejec.conocida = str(uuid4())
    repo = repo or RepoFalso(origen_filas=[(False, "Zapatillas", 3, 300, 2), (True, "Polo", 1, 50, 1)])
    llm = llm or LLMGuionado([texto("Listo.")])
    creados = []

    def crear_agente():
        creados.append(1)
        return Agente(llm, RegistroHerramientas(repo), ejecuciones=ejec)

    servicios = Servicios(historial, ejec, repo, crear_agente)
    app = crear_app(Ajustes(CLAVE, (), "prod", **ajustes), servicios)
    return TestClient(app, raise_server_exceptions=False), historial, ejec, llm, creados


@pytest.fixture
def ctx():
    return _montar()


RUTAS_PRIVADAS = [("get", "/v1/conversaciones"), ("post", "/v1/conversaciones"),
                  ("get", f"/v1/conversaciones/{uuid4()}/mensajes"), ("post", f"/v1/conversaciones/{uuid4()}/mensajes"),
                  ("get", f"/v1/conversaciones/{uuid4()}/ejecuciones"), ("get", f"/v1/ejecuciones/{uuid4()}"),
                  ("get", "/v1/reportes/ventas?periodo=este_mes"), ("get", "/v1/reportes/ventas.csv?periodo=este_mes")]


# ---- autenticación ----
@pytest.mark.parametrize("metodo,ruta", RUTAS_PRIVADAS)
def test_todas_las_rutas_privadas_exigen_bearer(ctx, metodo, ruta):
    cliente, _, _, llm, creados = ctx
    r = getattr(cliente, metodo)(ruta, **({"json": {"contenido": "hola"}} if metodo == "post" else {}))
    assert r.status_code == 401 and r.json()["error"]["codigo"] == "no_autenticado"
    assert not creados and not llm.llamadas


def test_fuerza_bruta_recibe_429_tras_10_fallos(ctx):
    cliente = ctx[0]
    malo = {"Authorization": "Bearer " + "x" * 40}
    codigos = [cliente.get("/v1/conversaciones", headers=malo).status_code for _ in range(12)]
    assert codigos[:10] == [401] * 10 and codigos[10:] == [429, 429]


# ---- conversaciones e historial ----
def test_crear_listar_y_leer_historial(ctx):
    cliente, historial, *_ = ctx
    r = cliente.post("/v1/conversaciones", headers=HDR)
    assert r.status_code == 201
    cid = r.json()["id"]
    assert [c["id"] for c in cliente.get("/v1/conversaciones", headers=HDR).json()] == [cid]
    historial.datos[cid] += [{"role": "user", "content": "hola"}, {"role": "assistant", "content": "qué tal"}]
    r = cliente.get(f"/v1/conversaciones/{cid}/mensajes?limite=1", headers=HDR)
    assert r.json() == [{"rol": "assistant", "contenido": "qué tal"}]


@pytest.mark.parametrize("ruta", ["/v1/conversaciones/no-es-uuid/mensajes", f"/v1/conversaciones/{uuid4()}/mensajes",
                                  f"/v1/conversaciones/{uuid4()}/ejecuciones", "/v1/ejecuciones/xyz",
                                  f"/v1/ejecuciones/{uuid4()}"])
def test_ids_invalidos_o_inexistentes_dan_404(ctx, ruta):
    r = ctx[0].get(ruta, headers=HDR)
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "no_encontrado"


@pytest.mark.parametrize("query", ["limite=0", "limite=101", "limite=abc"])
def test_limite_del_historial_validado(ctx, query):
    cid = ctx[1].crear()
    assert ctx[0].get(f"/v1/conversaciones/{cid}/mensajes?{query}", headers=HDR).status_code == 422


def test_ejecuciones_de_una_conversacion_y_detalle(ctx):
    cliente, historial, ejec, *_ = ctx
    cid = historial.crear()
    assert len(cliente.get(f"/v1/conversaciones/{cid}/ejecuciones", headers=HDR).json()) == 1
    d = cliente.get(f"/v1/ejecuciones/{ejec.conocida}", headers=HDR).json()
    assert d["herramientas"][0]["herramienta"] == "ventas_totales" and "pregunta" not in d


# ---- chat ----
def test_chat_usa_el_agente_y_guarda_el_turno():
    llm = LLMGuionado([llamada("ventas_totales", periodo="este_mes"), texto("Vendiste 1000.00 soles.")])
    cliente, historial, _, _, _ = _montar(llm=llm)
    cid = historial.crear()
    r = cliente.post(f"/v1/conversaciones/{cid}/mensajes", headers=HDR, json={"contenido": "  ¿Cuánto vendí? "})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "ok" and cuerpo["origen"] == "modelo" and cuerpo["ejecucion_id"] == "ejec-1"
    assert cuerpo["herramientas"][0]["nombre"] == "ventas_totales" and cuerpo["historial_guardado"] is True
    assert historial.datos[cid][0] == {"role": "user", "content": "¿Cuánto vendí?"}


def test_chat_conversacion_inexistente_404_y_sin_llamar_al_modelo(ctx):
    cliente, _, _, llm, _ = ctx
    r = cliente.post(f"/v1/conversaciones/{uuid4()}/mensajes", headers=HDR, json={"contenido": "hola"})
    assert r.status_code == 404 and not llm.llamadas


@pytest.mark.parametrize("cuerpo", [{}, {"contenido": ""}, {"contenido": "   "}, {"contenido": "x" * 4001},
                                    {"contenido": 5}, {"contenido": "hola", "extra": 1}])
def test_chat_valida_el_cuerpo_con_pydantic(ctx, cuerpo):
    cliente, historial, _, llm, creados = ctx
    r = cliente.post(f"/v1/conversaciones/{historial.crear()}/mensajes", headers=HDR, json=cuerpo)
    assert r.status_code == 422 and r.json()["error"]["codigo"] == "solicitud_invalida"
    assert not creados and not llm.llamadas


def test_chat_cuerpo_enorme_da_413(ctx):
    r = ctx[0].post(f"/v1/conversaciones/{uuid4()}/mensajes", headers=HDR, json={"contenido": "x" * 70_000})
    assert r.status_code == 413


def test_chat_limite_de_frecuencia_429_con_retry_after():
    cliente, historial, _, llm, _ = _montar(llm=LLMGuionado(repetir=texto("ok")), chat_por_minuto=2)
    cid = historial.crear()
    respuestas = [cliente.post(f"/v1/conversaciones/{cid}/mensajes", headers=HDR, json={"contenido": "hola"})
                  for _ in range(3)]
    assert [r.status_code for r in respuestas] == [200, 200, 429]
    assert int(respuestas[2].headers["retry-after"]) >= 1 and len(llm.llamadas) == 2


def test_chat_tope_de_concurrencia():
    cliente, historial, _, llm, _ = _montar()
    cid = historial.crear()
    sem = cliente.app.state.limitadores.chats_activos
    assert sem.acquire(blocking=False) and sem.acquire(blocking=False)  # simula 2 chats en curso
    r = cliente.post(f"/v1/conversaciones/{cid}/mensajes", headers=HDR, json={"contenido": "hola"})
    assert r.status_code == 429 and not llm.llamadas
    sem.release()
    sem.release()
    assert cliente.post(f"/v1/conversaciones/{cid}/mensajes", headers=HDR, json={"contenido": "hola"}).status_code == 200


def test_chat_libera_el_cupo_aunque_falle():
    cliente, historial, *_ = _montar()

    def falla():
        raise RuntimeError("password=secreto")

    cliente.app.state.servicios.crear_agente = falla
    r = cliente.post(f"/v1/conversaciones/{historial.crear()}/mensajes", headers=HDR, json={"contenido": "hola"})
    assert r.status_code == 500 and "secreto" not in r.text
    sem = cliente.app.state.limitadores.chats_activos
    assert sem.acquire(blocking=False) and sem.acquire(blocking=False)


def test_chat_sin_groq_configurado_da_503(ctx):
    def sin_llm():
        raise ServicioNoDisponible("llm_no_configurado", "no configurado")

    cliente, historial, *_ = ctx
    cliente.app.state.servicios.crear_agente = sin_llm
    r = cliente.post(f"/v1/conversaciones/{historial.crear()}/mensajes", headers=HDR, json={"contenido": "hola"})
    assert r.status_code == 503 and r.json()["error"]["codigo"] == "llm_no_configurado"


def test_chat_si_falla_el_historial_la_respuesta_no_se_pierde():
    cliente, historial, *_ = _montar()
    cid = historial.crear()
    historial.falla_al_agregar = True
    r = cliente.post(f"/v1/conversaciones/{cid}/mensajes", headers=HDR, json={"contenido": "hola"})
    assert r.status_code == 200 and r.json()["historial_guardado"] is False and "secreto" not in r.text


# ---- reportes ----
def test_reporte_json_separa_real_y_demo(ctx):
    r = ctx[0].get("/v1/reportes/ventas?periodo=este_mes", headers=HDR)
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo["origenes"]) == {"real", "demo"} and cuerpo["contiene_datos_demo"] is True
    assert cuerpo["origenes"]["real"]["total"]["ingresos"] == 300.0


def test_reporte_filtra_por_origen_y_compara():
    cliente = _montar(repo=RepoFalso(origen_filas=[[(False, "A", 1, 10, 1)], [(False, "A", 1, 5, 1)]]))[0]
    r = cliente.get("/v1/reportes/ventas?periodo=este_mes&comparar_con=mes_anterior&origen=real", headers=HDR)
    assert r.status_code == 200 and list(r.json()["origenes"]) == ["real"]
    assert r.json()["total_combinado"]["variacion_ingresos"] == 5.0


@pytest.mark.parametrize("query", ["", "periodo=hoy", "periodo=este_mes&origen=otro", "periodo=" + "x" * 41,
                                   "periodo=2030-01-01/2030-01-31", "periodo=este_mes&comparar_con="])
def test_reporte_rechaza_parametros_invalidos(ctx, query):
    assert ctx[0].get(f"/v1/reportes/ventas?{query}", headers=HDR).status_code == 422


def test_reporte_csv_en_memoria_con_cabeceras_de_descarga(ctx):
    r = ctx[0].get("/v1/reportes/ventas.csv?periodo=este_mes", headers=HDR)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert 'filename="reporte_ventas.csv"' in r.headers["content-disposition"]
    lineas = r.content.decode("utf-8-sig").splitlines()
    assert lineas[0].startswith("origen,producto") and any(linea.startswith("demo,Polo") for linea in lineas)


def test_fallo_de_la_base_en_reportes_da_500_generico():
    cliente = _montar(repo=RepoQueFalla())[0]
    r = cliente.get("/v1/reportes/ventas?periodo=este_mes", headers=HDR)
    assert r.status_code == 500 and r.json()["error"]["codigo"] == "error_interno"
    assert "secreto" not in r.text and "host=" not in r.text


def test_limite_de_lecturas():
    cliente = _montar(lecturas_por_minuto=2)[0]
    codigos = [cliente.get("/v1/conversaciones", headers=HDR).status_code for _ in range(3)]
    assert codigos == [200, 200, 429]


# ---- limitador ----
def test_ventana_deslizante_libera_cupo_con_el_tiempo():
    t = [0.0]
    lim = LimitadorVentana(2, 60, reloj=lambda: t[0])
    lim.consumir()
    lim.consumir()
    with pytest.raises(DemasiadasSolicitudes):
        lim.consumir()
    t[0] = 61
    lim.consumir()


def test_limitador_es_seguro_con_hilos():
    lim, ok, fallos = LimitadorVentana(5), [], []

    def usar():
        try:
            lim.consumir()
            ok.append(1)
        except DemasiadasSolicitudes:
            fallos.append(1)

    hilos = [threading.Thread(target=usar) for _ in range(20)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(ok) == 5 and len(fallos) == 15
