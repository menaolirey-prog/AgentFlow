"""Control de acceso: API key en cabecera `Authorization: Bearer <clave>`.

Decisión: una clave compartida basta mientras haya un solo usuario (el gerente) y ninguna conversación tenga
propietario. Si se añaden usuarios, se sustituye esta dependencia por JWT/OAuth sin tocar los routers.
"""
import hashlib
import hmac

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agentflow.api.errors import NoAutenticado, ServicioNoDisponible

esquema_bearer = HTTPBearer(auto_error=False, scheme_name="ApiKey", description="Clave de API de AgentFlow")


def _iguales(a: str, b: str) -> bool:
    """Comparación en tiempo constante (se comparan digests para no filtrar la longitud)."""
    return hmac.compare_digest(hashlib.sha256(a.encode()).digest(), hashlib.sha256(b.encode()).digest())


def requerir_api_key(request: Request,
                     credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> None:
    clave = request.app.state.ajustes.api_key
    if clave is None:  # fallo cerrado: sin clave configurada nadie entra
        raise ServicioNoDisponible("autenticacion_no_configurada", "La autenticación de la API no está configurada.")
    if credenciales is None or credenciales.scheme.lower() != "bearer" or not _iguales(credenciales.credentials, clave):
        request.app.state.limitadores.fallos_auth.consumir()  # 429 tras 10 fallos/min: frena la fuerza bruta
        raise NoAutenticado()
