import logging

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from agentflow.agent.orchestrator import Agente
from agentflow.api.app import crear_app
from agentflow.api.config import Ajustes, ErrorConfiguracion, cargar_ajustes
from agentflow.api.errors import ServicioNoDisponible
from agentflow.api.seguridad import requerir_api_key
from agentflow.api.servicios import Servicios, servicios_por_defecto
from agentflow.observability.logging import FormatoJSON

CLAVE = "k" * 40
HDR = {"Authorization": f"Bearer {CLAVE}"}


def _cliente(**kw):
    ajustes = Ajustes(api_key=kw.pop("api_key", CLAVE), origenes_cors=kw.pop("origenes", ()),
                      entorno=kw.pop("entorno", "prod"))
    app = crear_app(ajustes, Servicios(None, None, None, lambda: None))
    return TestClient(app, raise_server_exceptions=False), app


@pytest.fixture
def cliente():
    return _cliente()[0]


# ---- salud y cabeceras ----
def test_health_es_publico_y_añade_cabeceras_de_seguridad(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json() == {"estado": "ok", "version": "0.3.0"}
    assert len(r.headers["x-request-id"]) == 32
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"


def test_el_id_de_solicitud_lo_genera_el_servidor(cliente):
    r = cliente.get("/health", headers={"X-Request-ID": "inyectado\nfalso"})
    assert r.headers["x-request-id"] != "inyectado\nfalso"


# ---- autenticación ----
def test_sesion_con_clave_correcta(cliente):
    r = cliente.get("/v1/sesion", headers=HDR)
    assert r.status_code == 200 and r.json() == {"autenticado": True}


@pytest.mark.parametrize("cabeceras", [{}, {"Authorization": "Bearer " + "x" * 40}, {"Authorization": "Bearer "},
                                       {"Authorization": f"Basic {CLAVE}"}, {"Authorization": CLAVE}])
def test_sesion_rechaza_credenciales_ausentes_o_invalidas(cliente, cabeceras):
    r = cliente.get("/v1/sesion", headers=cabeceras)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    error = r.json()["error"]
    assert error["codigo"] == "no_autenticado" and error["solicitud_id"] == r.headers["x-request-id"]


def test_sin_clave_configurada_falla_cerrado():
    cliente, _ = _cliente(api_key=None)
    for hdr in ({}, HDR, {"Authorization": "Bearer "}):
        r = cliente.get("/v1/sesion", headers=hdr)
        assert r.status_code == 503 and r.json()["error"]["codigo"] == "autenticacion_no_configurada"
    assert cliente.get("/health").status_code == 200  # la salud sigue disponible


def test_la_clave_nunca_aparece_en_respuestas_ni_logs(caplog):
    cliente, _ = _cliente()
    with caplog.at_level(logging.INFO, logger="agentflow"):
        r = cliente.get("/v1/sesion?token=" + CLAVE, headers=HDR)
    registros = " ".join(FormatoJSON().format(rec) for rec in caplog.records)
    assert CLAVE not in r.text and CLAVE not in registros and "Authorization" not in registros
    http = next(rec for rec in caplog.records if rec.getMessage() == "http")
    assert http.campos["ruta"] == "/v1/sesion" and http.campos["estado"] == 200  # sin query string


def test_repr_de_ajustes_oculta_la_clave():
    assert CLAVE not in repr(Ajustes(CLAVE, (), "prod"))


# ---- errores centralizados ----
def test_ruta_inexistente_y_metodo_no_permitido(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "no_encontrado"
    r = cliente.post("/health")
    assert r.status_code == 405 and r.json()["error"]["codigo"] == "metodo_no_permitido"


def test_validacion_422_sin_reflejar_el_valor_enviado():
    cliente, app = _cliente()

    class Entrada(BaseModel):
        contenido: str = Field(min_length=1, max_length=5)

    @app.post("/v1/_prueba", dependencies=[Depends(requerir_api_key)])
    def prueba(e: Entrada):
        return {}

    r = cliente.post("/v1/_prueba", headers=HDR, json={"contenido": "SECRETO-MUY-LARGO"})
    assert r.status_code == 422 and "SECRETO" not in r.text
    error = r.json()["error"]
    assert error["codigo"] == "solicitud_invalida" and error["campos"][0]["campo"] == "body.contenido"


def test_error_inesperado_da_500_generico_sin_detalles(caplog):
    cliente, app = _cliente()

    @app.get("/v1/_boom", dependencies=[Depends(requerir_api_key)])
    def boom():
        raise RuntimeError("password=abc host=interno")

    with caplog.at_level(logging.INFO, logger="agentflow"):
        r = cliente.get("/v1/_boom", headers=HDR)
    assert r.status_code == 500 and r.json()["error"]["codigo"] == "error_interno"
    assert "password=abc" not in r.text and "host=" not in r.text and r.headers["x-request-id"]
    assert "abc" not in " ".join(FormatoJSON().format(rec) for rec in caplog.records)


def test_error_de_dominio_con_su_codigo_http():
    cliente, app = _cliente()

    @app.get("/v1/_llm", dependencies=[Depends(requerir_api_key)])
    def llm():
        raise ServicioNoDisponible("llm_no_configurado", "El servicio de lenguaje no está configurado.")

    r = cliente.get("/v1/_llm", headers=HDR)
    assert r.status_code == 503 and r.json()["error"]["codigo"] == "llm_no_configurado"


def test_cuerpo_demasiado_grande_se_rechaza_antes_de_procesar(cliente):
    r = cliente.post("/v1/sesion", headers={**HDR, "Content-Length": "70000"}, content=b"x")
    assert r.status_code == 413 and r.json()["error"]["codigo"] == "cuerpo_demasiado_grande"


# ---- CORS ----
def test_cors_permite_solo_los_origenes_configurados():
    cliente, _ = _cliente(origenes=("http://localhost:5173",))
    pre = cliente.options("/v1/sesion", headers={"Origin": "http://localhost:5173",
                                                 "Access-Control-Request-Method": "GET",
                                                 "Access-Control-Request-Headers": "authorization"})
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in pre.headers
    assert "DELETE" not in pre.headers["access-control-allow-methods"]
    ajeno = cliente.get("/health", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in ajeno.headers
    propio = cliente.get("/v1/sesion", headers={**HDR, "Origin": "http://localhost:5173"})
    assert propio.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-request-id" in propio.headers["access-control-expose-headers"].lower()


def test_sin_origenes_configurados_no_hay_cors(cliente):
    r = cliente.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in r.headers


# ---- documentación solo en dev ----
def test_docs_solo_en_dev():
    prod, _ = _cliente(entorno="prod")
    assert prod.get("/docs").status_code == 404 and prod.get("/openapi.json").status_code == 404
    dev, _ = _cliente(entorno="dev")
    assert dev.get("/docs").status_code == 200
    esquema = dev.get("/openapi.json").json()
    assert {"/health", "/v1/sesion"} <= set(esquema["paths"])
    assert "ApiKey" in esquema["components"]["securitySchemes"]


# ---- configuración ----
def test_ajustes_por_defecto_son_restrictivos():
    a = cargar_ajustes({})
    assert (a.api_key, a.origenes_cors, a.entorno, a.docs_habilitada) == (None, (), "prod", False)


def test_ajustes_validos():
    a = cargar_ajustes({"AGENTFLOW_API_KEY": CLAVE, "AGENTFLOW_ENV": "DEV",
                        "AGENTFLOW_CORS_ORIGINS": "http://localhost:5173/, https://app.example.com"})
    assert a.origenes_cors == ("http://localhost:5173", "https://app.example.com") and a.docs_habilitada


@pytest.mark.parametrize("env", [{"AGENTFLOW_API_KEY": "corta"}, {"AGENTFLOW_CORS_ORIGINS": "*"},
                                 {"AGENTFLOW_CORS_ORIGINS": "http://*.example.com"},
                                 {"AGENTFLOW_CORS_ORIGINS": "http://a.com/ruta"}, {"AGENTFLOW_ENV": "staging"}])
def test_ajustes_invalidos_impiden_arrancar(env):
    with pytest.raises(ErrorConfiguracion) as e:
        cargar_ajustes(env)
    assert "corta" not in str(e.value)


# ---- servicios ----
def test_agente_se_crea_perezosamente_y_exige_clave_de_groq(monkeypatch):
    servicios = servicios_por_defecto()  # no conecta a la base ni a Groq
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ServicioNoDisponible) as e:
        servicios.crear_agente()
    assert e.value.status == 503 and e.value.codigo == "llm_no_configurado"
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    assert isinstance(servicios.crear_agente(), Agente)  # construir el cliente no hace red
