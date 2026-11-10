"""Configuración de la API, leída del entorno (.env). Nunca incluye valores secretos en los mensajes de error."""
import os
import re
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv

MIN_LONGITUD_CLAVE = 32
_ORIGEN = re.compile(r"^https?://[^/*\s]+$")


class ErrorConfiguracion(Exception):
    """Configuración inválida: la API se niega a arrancar antes que operar de forma insegura."""


@dataclass(frozen=True)
class Ajustes:
    api_key: str | None            # None => los endpoints protegidos responden 503 (fallo cerrado)
    origenes_cors: tuple[str, ...]  # vacío => sin CORS (ningún navegador de otro origen puede llamar)
    entorno: str                    # "dev" | "prod"
    chat_por_minuto: int = 10       # mensajes de chat/min (cada uno consume cuota de Groq)
    lecturas_por_minuto: int = 120  # lecturas, reportes y creaciones/min

    @property
    def docs_habilitada(self) -> bool:
        return self.entorno == "dev"

    def __repr__(self) -> str:      # evita que la clave aparezca en logs o trazas
        return f"Ajustes(api_key={'***' if self.api_key else None}, origenes_cors={self.origenes_cors}, entorno={self.entorno!r})"


def cargar_ajustes(env: Mapping[str, str] | None = None) -> Ajustes:
    if env is None:
        load_dotenv()
        env = os.environ
    clave = (env.get("AGENTFLOW_API_KEY") or "").strip() or None
    if clave is not None and len(clave) < MIN_LONGITUD_CLAVE:
        raise ErrorConfiguracion(f"AGENTFLOW_API_KEY debe tener al menos {MIN_LONGITUD_CLAVE} caracteres")
    origenes = tuple(o.strip().rstrip("/") for o in (env.get("AGENTFLOW_CORS_ORIGINS") or "").split(",") if o.strip())
    for origen in origenes:
        if not _ORIGEN.match(origen):  # rechaza '*' y valores con rutas o comodines
            raise ErrorConfiguracion("AGENTFLOW_CORS_ORIGINS solo admite orígenes explícitos (http(s)://host[:puerto])")
    entorno = (env.get("AGENTFLOW_ENV") or "prod").strip().lower()
    if entorno not in ("dev", "prod"):
        raise ErrorConfiguracion("AGENTFLOW_ENV debe ser 'dev' o 'prod'")
    chat = _entero(env, "AGENTFLOW_CHAT_POR_MINUTO", 10)
    return Ajustes(api_key=clave, origenes_cors=origenes, entorno=entorno, chat_por_minuto=chat)


def _entero(env: Mapping[str, str], nombre: str, defecto: int) -> int:
    texto = (env.get(nombre) or "").strip()
    if not texto:
        return defecto
    if not texto.isdigit() or not 1 <= int(texto) <= 1000:
        raise ErrorConfiguracion(f"{nombre} debe ser un entero entre 1 y 1000")
    return int(texto)
