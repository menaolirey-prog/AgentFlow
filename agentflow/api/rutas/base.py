"""Rutas base: salud (pública) y verificación de credenciales (protegida)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agentflow.api.errors import ErrorRespuesta
from agentflow.api.seguridad import requerir_api_key

publico = APIRouter(tags=["Salud"])
protegido = APIRouter(prefix="/v1", tags=["Sesión"], dependencies=[Depends(requerir_api_key)],
                      responses={401: {"model": ErrorRespuesta}, 503: {"model": ErrorRespuesta}})


class EstadoSalud(BaseModel):
    estado: str
    version: str


class EstadoSesion(BaseModel):
    autenticado: bool


@publico.get("/health", response_model=EstadoSalud, summary="Liveness (sin autenticación ni base de datos)")
def salud() -> EstadoSalud:
    from agentflow.api.app import VERSION
    return EstadoSalud(estado="ok", version=VERSION)


@protegido.get("/sesion", response_model=EstadoSesion, summary="Comprueba que la clave de API es válida")
def sesion() -> EstadoSesion:
    return EstadoSesion(autenticado=True)
