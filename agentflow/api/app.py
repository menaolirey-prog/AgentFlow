"""Fábrica de la aplicación FastAPI.

Ejecutar:  .venv\\Scripts\\python.exe -m uvicorn agentflow.api.app:crear_app_desde_entorno --factory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from agentflow.api.config import Ajustes, cargar_ajustes
from agentflow.api.errors import registrar_manejadores
from agentflow.api.middleware import middleware_solicitud
from agentflow.api.limites import Limitadores
from agentflow.api.rutas import base, conversaciones, ejecuciones, reportes
from agentflow.api.servicios import Servicios, servicios_por_defecto
from agentflow.observability.logging import configurar_archivo

VERSION = "0.3.0"


def crear_app(ajustes: Ajustes, servicios: Servicios) -> FastAPI:
    docs = ajustes.docs_habilitada
    app = FastAPI(title="AgentFlow API", version=VERSION,
                  description="API del agente comercial de AgentFlow (datos ficticios de demostración).",
                  docs_url="/docs" if docs else None, redoc_url=None,
                  openapi_url="/openapi.json" if docs else None)
    app.state.ajustes, app.state.servicios = ajustes, servicios
    app.state.limitadores = Limitadores(ajustes.chat_por_minuto, ajustes.lecturas_por_minuto)
    registrar_manejadores(app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=middleware_solicitud)
    if ajustes.origenes_cors:  # se añade el último: CORS queda como capa más externa (también cubre errores)
        app.add_middleware(CORSMiddleware, allow_origins=list(ajustes.origenes_cors), allow_credentials=False,
                           allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"],
                           expose_headers=["X-Request-ID"], max_age=600)
    app.include_router(base.publico)
    for router in (base.protegido, conversaciones.router, ejecuciones.router, reportes.router):
        app.include_router(router)
    return app


def crear_app_desde_entorno() -> FastAPI:
    configurar_archivo("logs/agentflow.jsonl")
    return crear_app(cargar_ajustes(), servicios_por_defecto())
