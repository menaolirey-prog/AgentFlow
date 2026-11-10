"""Dobles de prueba: ningún test unitario toca red ni PostgreSQL."""
import copy
import json
from datetime import date
from decimal import Decimal

from agentflow.db.repositories.ventas import ResumenVentas
from agentflow.llm.base import ErrorLLM, LlamadaModelo, RespuestaLLM

HOY = date(2026, 11, 10)


def texto(contenido: str, **kw) -> RespuestaLLM:
    return RespuestaLLM(contenido=contenido, **kw)


def llamada(nombre: str, _id: str = "c1", **argumentos) -> RespuestaLLM:
    return RespuestaLLM(llamadas=[LlamadaModelo(_id, nombre, json.dumps(argumentos))],
                        finish_reason="tool_calls", tokens_entrada=100, tokens_salida=20)


class LLMGuionado:
    """Devuelve respuestas en orden; si se agotan, repite `repetir` (o falla)."""

    def __init__(self, respuestas=(), repetir=None):
        self.respuestas, self.repetir, self.llamadas = list(respuestas), repetir, []

    def chat(self, mensajes, herramientas, tool_choice):
        self.llamadas.append({"mensajes": copy.deepcopy(mensajes), "tool_choice": tool_choice})
        if self.respuestas:
            r = self.respuestas.pop(0)
        elif self.repetir is not None:
            r = self.repetir
        else:
            raise AssertionError("el LLM simulado se quedó sin respuestas")
        if isinstance(r, ErrorLLM):
            raise r
        return r


class RepoFalso:
    """Repositorio en memoria con resultados fijos; registra las llamadas."""

    def __init__(self, resumen=ResumenVentas(Decimal("1000.00"), 10, 4), productos=(), caidas=()):
        self._resumen, self._productos, self._caidas = resumen, list(productos), list(caidas)
        self.llamadas = []

    def resumen(self, inicio, fin_exclusivo):
        self.llamadas.append(("resumen", inicio, fin_exclusivo))
        r = self._resumen
        return r.pop(0) if isinstance(r, list) else r

    def por_producto(self, inicio, fin_exclusivo, ordenar_por, limite):
        self.llamadas.append(("por_producto", inicio, fin_exclusivo, ordenar_por, limite))
        return self._productos

    def caidas(self, actual, anterior, limite):
        self.llamadas.append(("caidas", actual, anterior, limite))
        return self._caidas


class RepoQueFalla:
    def __getattr__(self, _):
        def falla(*a, **k):
            raise RuntimeError("password=secreto host=interno")
        return falla
