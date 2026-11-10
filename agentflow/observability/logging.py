"""Eventos JSON-lines. Nunca se registran claves ni el texto de las preguntas."""
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("agentflow")
_SENSIBLE = re.compile(r"key|password|secret|authorization|contrasena", re.IGNORECASE)


def registrar(evento: str, **campos) -> None:
    seguros = {k: ("***" if _SENSIBLE.search(k) else v) for k, v in campos.items()}
    logger.info(evento, extra={"campos": seguros})


class FormatoJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "evento": record.getMessage()}
        return json.dumps({**base, **getattr(record, "campos", {})}, ensure_ascii=False, default=str)


def configurar_archivo(ruta: str | Path) -> None:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    manejador = logging.FileHandler(ruta, encoding="utf-8")
    manejador.setFormatter(FormatoJSON())
    logger.addHandler(manejador)
    logger.setLevel(logging.INFO)
    logger.propagate = False
