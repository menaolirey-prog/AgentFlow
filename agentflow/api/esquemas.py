"""Modelos Pydantic de entrada y salida de la API (la validación ocurre aquí, antes de tocar el agente o la base)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_MENSAJE = 4000


class NuevoMensaje(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    contenido: str = Field(min_length=1, max_length=MAX_MENSAJE)


class ConversacionCreada(BaseModel):
    id: str


class ConversacionResumen(BaseModel):
    id: str
    creada_en: datetime
    mensajes: int
    inicio: str | None = None


class Mensaje(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class HerramientaUsada(BaseModel):
    nombre: str
    ok: bool
    codigo_error: str | None = None
    duracion_ms: int


class RespuestaChat(BaseModel):
    respuesta: str
    estado: str
    motivo: str | None = None
    origen: str
    herramientas: list[HerramientaUsada]
    tokens_entrada: int
    tokens_salida: int
    duracion_ms: int
    ejecucion_id: str | None = None
    historial_guardado: bool


class EjecucionResumen(BaseModel):
    id: str
    estado: str
    motivo: str | None = None
    origen: str | None = None
    tokens: int
    duracion_ms: int | None = None
    iniciada_en: datetime
    herramientas: int


class HerramientaEjecutada(BaseModel):
    orden: int
    herramienta: str
    argumentos: dict | None = None
    ok: bool
    codigo_error: str | None = None
    duracion_ms: int


class EjecucionDetalle(BaseModel):
    id: str
    conversacion_id: str | None = None
    estado: str
    motivo: str | None = None
    origen: str | None = None
    pregunta_chars: int
    tokens_entrada: int
    tokens_salida: int
    llamadas_llm: int
    duracion_ms: int | None = None
    iniciada_en: datetime
    finalizada_en: datetime | None = None
    herramientas: list[HerramientaEjecutada]
