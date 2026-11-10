"""Conversación: historial en memoria, con persistencia opcional por sesión."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from agentflow.observability.logging import registrar

if TYPE_CHECKING:
    from agentflow.agent.orchestrator import ResultadoAgente

LIMITE_CARGA = 50  # mensajes recuperados al reanudar (el agente solo usa los más recientes)


class ConversacionNoEncontrada(Exception):
    pass


class AlmacenHistorial(Protocol):
    def crear(self) -> str: ...
    def agregar(self, conversacion_id: str, mensajes: list[tuple[str, str]]) -> None: ...
    def cargar(self, conversacion_id: str, limite: int) -> list[dict] | None: ...


@dataclass
class Conversacion:
    mensajes: list[dict] = field(default_factory=list)
    ultimo_resultado: "ResultadoAgente | None" = None
    id: str | None = None
    almacen: AlmacenHistorial | None = None
    persistencia_ok: bool = True

    @classmethod
    def nueva(cls, almacen: AlmacenHistorial) -> "Conversacion":
        return cls(id=almacen.crear(), almacen=almacen)

    @classmethod
    def reanudar(cls, almacen: AlmacenHistorial, conversacion_id: str) -> "Conversacion":
        identificador = str(UUID(conversacion_id))  # ValueError si no es un UUID válido
        mensajes = almacen.cargar(identificador, LIMITE_CARGA)
        if mensajes is None:
            raise ConversacionNoEncontrada(identificador)
        return cls(mensajes=mensajes, id=identificador, almacen=almacen)

    def recientes(self, maximo: int) -> list[dict]:
        return self.mensajes[-maximo:]

    def registrar_turno(self, pregunta: str, respuesta: str) -> None:
        """Guarda el turno en memoria y, si hay almacén, en la base. Un fallo de la base no pierde la respuesta."""
        self.mensajes += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": respuesta}]
        if self.almacen is None or self.id is None:
            return
        try:
            self.almacen.agregar(self.id, [("user", pregunta), ("assistant", respuesta)])
        except Exception as error:  # el detalle puede contener datos de conexión: solo el tipo va al log
            self.persistencia_ok = False
            registrar("error_historial", tipo=type(error).__name__)
