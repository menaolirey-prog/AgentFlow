"""Contrato común de los proveedores LLM. El orquestador solo conoce estos tipos."""
from dataclasses import dataclass, field
from typing import Protocol


class ErrorLLM(Exception):
    """Fallo del proveedor. `codigo`: limite_tasa | conexion | estado_http | respuesta_invalida."""

    def __init__(self, codigo: str, detalle: str = ""):
        super().__init__(codigo)
        self.codigo = codigo
        self.detalle = detalle


@dataclass(frozen=True)
class LlamadaModelo:
    id: str
    nombre: str
    argumentos: str  # JSON crudo tal como lo emitió el modelo; se valida en el registro


@dataclass
class RespuestaLLM:
    contenido: str | None = None
    llamadas: list[LlamadaModelo] = field(default_factory=list)
    finish_reason: str = "stop"
    tokens_entrada: int = 0
    tokens_salida: int = 0


class ClienteLLM(Protocol):
    def chat(self, mensajes: list[dict], herramientas: list[dict], tool_choice: str) -> RespuestaLLM: ...
