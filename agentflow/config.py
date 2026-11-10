"""Configuración central. Los límites los hace cumplir el código, no el prompt."""
from dataclasses import dataclass
from datetime import timedelta, timezone

MODELO = "openai/gpt-oss-20b"
MONEDA = "PEN"
# Perú no usa horario de verano: un desfase fijo equivale a America/Lima (y evita depender de tzdata).
ZONA_LIMA = timezone(timedelta(hours=-5), "America/Lima")


@dataclass(frozen=True)
class Limites:
    """Valores iniciales propuestos; se calibran con las evaluaciones."""
    max_iteraciones: int = 4
    max_llamadas_herramienta: int = 6
    timeout_total_s: float = 30.0
    timeout_llm_s: float = 20.0
    max_tokens_respuesta: int = 800     # por llamada; en gpt-oss incluye el razonamiento
    max_tokens_total: int = 8000        # entrada + salida acumuladas por solicitud
    max_historial_mensajes: int = 10
