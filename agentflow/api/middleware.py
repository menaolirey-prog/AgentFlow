"""Middleware transversal: ID de solicitud, límite de tamaño, cabeceras de seguridad y log de acceso."""
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from agentflow.observability.logging import registrar

MAX_CUERPO_BYTES = 64 * 1024  # el chat envía texto corto; 64 KB sobra
_CABECERAS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}  # datos privados: nada de caché


def _error(status: int, codigo: str, mensaje: str, solicitud_id: str) -> JSONResponse:
    return JSONResponse({"error": {"codigo": codigo, "mensaje": mensaje, "solicitud_id": solicitud_id}},
                        status_code=status)


async def middleware_solicitud(request: Request, call_next):
    # El ID lo genera el servidor (nunca se acepta del cliente: evitaría inyección en logs).
    solicitud_id = request.state.solicitud_id = uuid4().hex
    inicio = time.monotonic()
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > MAX_CUERPO_BYTES:
        respuesta = _error(413, "cuerpo_demasiado_grande", "La solicitud supera el tamaño permitido.", solicitud_id)
    else:
        try:
            respuesta = await call_next(request)
        except Exception as error:  # último recurso; el detalle nunca sale al cliente
            registrar("error_api", tipo=type(error).__name__, solicitud_id=solicitud_id)
            respuesta = _error(500, "error_interno", "Error interno del servidor.", solicitud_id)
    respuesta.headers["X-Request-ID"] = solicitud_id
    for nombre, valor in _CABECERAS.items():
        respuesta.headers[nombre] = valor
    # Sin query string, cabeceras ni cuerpo: pueden contener credenciales o texto del usuario.
    registrar("http", metodo=request.method, ruta=request.url.path, estado=respuesta.status_code,
              duracion_ms=int((time.monotonic() - inicio) * 1000), solicitud_id=solicitud_id)
    return respuesta
