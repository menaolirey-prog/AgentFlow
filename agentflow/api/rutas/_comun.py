"""Piezas compartidas por los routers de negocio."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from agentflow.api.errors import ErrorRespuesta, NoEncontrado
from agentflow.api.seguridad import requerir_api_key
from agentflow.api.servicios import Servicios, obtener_servicios


def router_privado(etiqueta: str) -> APIRouter:
    return APIRouter(prefix="/v1", tags=[etiqueta], dependencies=[Depends(requerir_api_key)],
                     responses={401: {"model": ErrorRespuesta}, 429: {"model": ErrorRespuesta},
                                503: {"model": ErrorRespuesta}})


def limitar_lectura(request: Request) -> None:
    request.app.state.limitadores.lecturas.consumir()


def uuid_o_404(valor: str, mensaje: str) -> str:
    """Un identificador mal formado es 'no encontrado' (no llega a la base ni se refleja en el error)."""
    try:
        return str(UUID(valor))
    except ValueError:
        raise NoEncontrado(mensaje) from None


__all__ = ["Servicios", "obtener_servicios", "router_privado", "limitar_lectura", "uuid_o_404"]
