"""Límites de uso en memoria (un solo proceso, un solo usuario): ventana deslizante y tope de concurrencia.

Como hay una única clave compartida, el límite es global y no por cliente. Con varios procesos o usuarios haría
falta un almacén compartido (p. ej. Redis) o el límite del proxy.
"""
import threading
import time
from collections import deque
from typing import Callable

from agentflow.api.errors import DemasiadasSolicitudes


class LimitadorVentana:
    def __init__(self, maximo: int, ventana_s: float = 60.0, reloj: Callable[[], float] = time.monotonic):
        self._max, self._ventana, self._reloj = maximo, ventana_s, reloj
        self._marcas: deque[float] = deque()
        self._cerrojo = threading.Lock()

    def consumir(self) -> None:
        """Registra una solicitud o lanza 429 con Retry-After."""
        with self._cerrojo:
            ahora = self._reloj()
            while self._marcas and ahora - self._marcas[0] >= self._ventana:
                self._marcas.popleft()
            if len(self._marcas) >= self._max:
                raise DemasiadasSolicitudes(int(self._ventana - (ahora - self._marcas[0])) + 1)
            self._marcas.append(ahora)


class Limitadores:
    """Chat (caro: consume Groq), tope de chats simultáneos y lecturas/escrituras baratas."""
    MAX_CHATS_SIMULTANEOS = 2

    def __init__(self, chat_por_minuto: int, lecturas_por_minuto: int, reloj: Callable[[], float] = time.monotonic):
        self.chat = LimitadorVentana(chat_por_minuto, reloj=reloj)
        self.lecturas = LimitadorVentana(lecturas_por_minuto, reloj=reloj)
        self.fallos_auth = LimitadorVentana(10, reloj=reloj)  # intentos con clave inválida por minuto
        self.chats_activos = threading.BoundedSemaphore(self.MAX_CHATS_SIMULTANEOS)
