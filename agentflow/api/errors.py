"""Errores de la API: un único formato JSON, sin valores de entrada ni detalles internos."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentflow.observability.logging import registrar


class CampoInvalido(BaseModel):
    campo: str
    mensaje: str


class DetalleError(BaseModel):
    codigo: str
    mensaje: str
    solicitud_id: str | None = None
    campos: list[CampoInvalido] | None = None


class ErrorRespuesta(BaseModel):
    error: DetalleError


class ErrorAPI(Exception):
    """Error de dominio con código HTTP. `mensaje` es seguro para mostrar al cliente."""

    def __init__(self, status: int, codigo: str, mensaje: str, headers: dict[str, str] | None = None):
        super().__init__(codigo)
        self.status, self.codigo, self.mensaje, self.headers = status, codigo, mensaje, headers


class NoAutenticado(ErrorAPI):
    def __init__(self):
        super().__init__(401, "no_autenticado", "Credenciales ausentes o inválidas.",
                         {"WWW-Authenticate": "Bearer"})


class NoEncontrado(ErrorAPI):
    def __init__(self, mensaje: str = "Recurso no encontrado."):
        super().__init__(404, "no_encontrado", mensaje)


class ServicioNoDisponible(ErrorAPI):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(503, codigo, mensaje)


class DemasiadasSolicitudes(ErrorAPI):
    def __init__(self, reintentar_en_s: int, mensaje: str = "Demasiadas solicitudes. Intenta de nuevo en unos instantes."):
        super().__init__(429, "demasiadas_solicitudes", mensaje, {"Retry-After": str(max(1, reintentar_en_s))})


def respuesta_error(request: Request, status: int, codigo: str, mensaje: str,
                    campos: list[dict] | None = None, headers: dict[str, str] | None = None) -> JSONResponse:
    cuerpo = ErrorRespuesta(error=DetalleError(
        codigo=codigo, mensaje=mensaje, solicitud_id=getattr(request.state, "solicitud_id", None),
        campos=[CampoInvalido(**c) for c in campos] if campos else None))
    return JSONResponse(cuerpo.model_dump(exclude_none=True), status_code=status, headers=headers)


_HTTP = {404: ("no_encontrado", "Recurso no encontrado."),
         405: ("metodo_no_permitido", "Método no permitido para este recurso."),
         429: ("demasiadas_solicitudes", "Demasiadas solicitudes."),
         413: ("cuerpo_demasiado_grande", "La solicitud supera el tamaño permitido.")}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorAPI)
    async def _error_api(request: Request, error: ErrorAPI):
        return respuesta_error(request, error.status, error.codigo, error.mensaje, headers=error.headers)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, error: RequestValidationError):
        # Solo ubicación y mensaje: nunca 'input', que podría reflejar datos del usuario.
        campos = [{"campo": ".".join(str(p) for p in e["loc"]), "mensaje": str(e["msg"])} for e in error.errors()]
        return respuesta_error(request, 422, "solicitud_invalida", "La solicitud no es válida.", campos=campos)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, error: StarletteHTTPException):
        codigo, mensaje = _HTTP.get(error.status_code, ("error_http", "No se pudo procesar la solicitud."))
        return respuesta_error(request, error.status_code, codigo, mensaje, headers=getattr(error, "headers", None))

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, error: Exception):
        registrar("error_api", tipo=type(error).__name__, solicitud_id=getattr(request.state, "solicitud_id", None))
        return respuesta_error(request, 500, "error_interno", "Error interno del servidor.")
