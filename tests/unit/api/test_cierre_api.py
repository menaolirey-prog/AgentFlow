"""Cierre de la Fase 3: OpenAPI, CORS para React local y no exposición de la clave. Solo dobles, sin red."""
import logging
from uuid import uuid4

from fastapi.testclient import TestClient

from agentflow.api.app import crear_app
from agentflow.api.config import cargar_ajustes
from agentflow.api.servicios import Servicios
from agentflow.observability.logging import FormatoJSON
from tests.unit.api.test_endpoints_api import CLAVE, HDR, _montar

REACT = "http://localhost:5173"
RUTAS = {"/health": {"get"}, "/v1/sesion": {"get"}, "/v1/conversaciones": {"get", "post"},
         "/v1/conversaciones/{conversacion_id}/mensajes": {"get", "post"},
         "/v1/conversaciones/{conversacion_id}/ejecuciones": {"get"}, "/v1/ejecuciones/{ejecucion_id}": {"get"},
         "/v1/reportes/ventas": {"get"}, "/v1/reportes/ventas.csv": {"get"}}


def _dev(**env):
    ajustes = cargar_ajustes({"AGENTFLOW_API_KEY": CLAVE, "AGENTFLOW_ENV": "dev",
                              "AGENTFLOW_CORS_ORIGINS": REACT, **env})
    base = _montar()
    servicios = base[0].app.state.servicios
    return TestClient(crear_app(ajustes, Servicios(servicios.historial, servicios.ejecuciones, servicios.ventas,
                                                  servicios.crear_agente)), raise_server_exceptions=False)


def test_openapi_en_dev_refleja_endpoints_metodos_y_errores():
    c = _dev()
    assert c.get("/docs").status_code == 200
    esquema = c.get("/openapi.json").json()
    for ruta, metodos in RUTAS.items():
        assert metodos <= set(esquema["paths"][ruta]), ruta
    chat = esquema["paths"]["/v1/conversaciones/{conversacion_id}/mensajes"]["post"]
    assert {"200", "401", "404", "422", "429", "503"} <= set(chat["responses"])
    assert esquema["paths"]["/v1/conversaciones"]["post"]["responses"]["201"]
    assert "ApiKey" in esquema["components"]["securitySchemes"]
    assert esquema["paths"]["/v1/reportes/ventas.csv"]["get"]["responses"]["200"]
    assert "/health" in esquema["paths"] and "security" not in esquema["paths"]["/health"]["get"]
    assert esquema["paths"]["/v1/sesion"]["get"]["security"]


def test_openapi_y_docs_no_existen_en_prod():
    c = _montar()[0]
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_openapi_no_contiene_la_clave():
    assert CLAVE not in _dev().get("/openapi.json").text


def test_preflight_de_react_local_permitido_y_origen_ajeno_rechazado():
    c = _dev()
    pedido = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}
    ok = c.options("/v1/conversaciones/x/mensajes", headers={"Origin": REACT, **pedido})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == REACT
    assert "access-control-allow-credentials" not in ok.headers and ok.headers["access-control-allow-origin"] != "*"
    mal = c.options("/v1/conversaciones/x/mensajes", headers={"Origin": "http://evil.example", **pedido})
    assert mal.status_code == 400 and "access-control-allow-origin" not in mal.headers
    borrar = c.options("/v1/conversaciones", headers={"Origin": REACT, "Access-Control-Request-Method": "DELETE"})
    assert borrar.status_code == 400


def test_errores_y_descargas_llevan_cors_y_exponen_request_id():
    c = _dev()
    r = c.get("/v1/reportes/ventas.csv?periodo=este_mes", headers={**HDR, "Origin": REACT})
    assert r.headers["access-control-allow-origin"] == REACT and "x-request-id" in r.headers["access-control-expose-headers"].lower()
    r = c.get("/v1/conversaciones", headers={"Origin": REACT})  # 401 también visible para el navegador
    assert r.status_code == 401 and r.headers["access-control-allow-origin"] == REACT


def test_la_clave_no_aparece_en_ninguna_respuesta_ni_log(caplog):
    cliente, historial, *_ = _montar()
    cid = historial.crear()
    pruebas = [("get", "/v1/conversaciones", {}), ("get", f"/v1/conversaciones/{cid}/mensajes", {}),
               ("post", f"/v1/conversaciones/{cid}/mensajes", {"json": {"contenido": "hola"}}),
               ("post", f"/v1/conversaciones/{uuid4()}/mensajes", {"json": {"contenido": ""}}),
               ("get", "/v1/reportes/ventas?periodo=este_mes", {}), ("get", "/v1/reportes/ventas?periodo=" + CLAVE, {})]
    textos = []
    with caplog.at_level(logging.INFO, logger="agentflow"):
        for metodo, ruta, kw in pruebas:
            for cabeceras in (HDR, {"Authorization": f"Bearer {CLAVE}x"}):
                r = getattr(cliente, metodo)(ruta, headers=cabeceras, **kw)
                textos.append(r.text + str(dict(r.headers)))
    registros = " ".join(FormatoJSON().format(rec) for rec in caplog.records)
    assert CLAVE not in "".join(textos) and CLAVE not in registros and "Bearer" not in registros
