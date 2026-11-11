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

    def __init__(self, resumen=ResumenVentas(Decimal("1000.00"), 10, 4), productos=(), caidas=(), origen_filas=(), origenes=(True, False)):
        self._resumen, self._productos, self._caidas = resumen, list(productos), list(caidas)
        self._origen = origen_filas  # lista de filas, o lista de listas (una por llamada)
        self._origenes = origenes
        self.llamadas = []

    def resumen(self, inicio, fin_exclusivo):
        self.llamadas.append(("resumen", inicio, fin_exclusivo))
        r = self._resumen
        return r.pop(0) if isinstance(r, list) else r

    def por_origen_producto(self, inicio, fin_exclusivo):
        self.llamadas.append(("por_origen_producto", inicio, fin_exclusivo))
        o = self._origen
        return o.pop(0) if o and isinstance(o[0], list) else list(o)

    def origenes(self, inicio, fin_exclusivo):
        return self._origenes

    def por_producto(self, inicio, fin_exclusivo, ordenar_por, limite):
        self.llamadas.append(("por_producto", inicio, fin_exclusivo, ordenar_por, limite))
        return self._productos

    def caidas(self, actual, anterior, limite):
        self.llamadas.append(("caidas", actual, anterior, limite))
        return self._caidas


class AlmacenEnMemoria:
    """Almacén de historial en memoria con la misma interfaz que HistorialPostgres."""

    def __init__(self, falla_al_agregar=False):
        self.datos, self.falla_al_agregar = {}, falla_al_agregar

    def crear(self):
        from uuid import uuid4
        nuevo = str(uuid4())
        self.datos[nuevo] = []
        return nuevo

    def agregar(self, conversacion_id, mensajes):
        if self.falla_al_agregar:
            raise RuntimeError("postgres caído password=secreto")
        self.datos[conversacion_id] += [{"role": r, "content": c} for r, c in mensajes]

    def cargar(self, conversacion_id, limite):
        return list(self.datos[conversacion_id][-limite:]) if conversacion_id in self.datos else None


class EjecucionesFalso:
    """Registro de ejecuciones en memoria con la interfaz de RegistroEjecuciones."""

    def __init__(self, falla_iniciar=False, falla_finalizar=False):
        self.iniciadas, self.finalizadas = [], []
        self.falla_iniciar, self.falla_finalizar = falla_iniciar, falla_finalizar

    def iniciar(self, conversacion_id, pregunta_chars):
        if self.falla_iniciar:
            raise RuntimeError("db caída password=secreto")
        self.iniciadas.append((conversacion_id, pregunta_chars))
        return f"ejec-{len(self.iniciadas)}"

    def finalizar(self, ejecucion_id, estado, motivo, origen, t_in, t_out, llamadas, duracion_ms, herramientas):
        if self.falla_finalizar:
            raise RuntimeError("db caída")
        self.finalizadas.append(dict(id=ejecucion_id, estado=estado, motivo=motivo, origen=origen, t_in=t_in,
                                     t_out=t_out, llamadas=llamadas, duracion_ms=duracion_ms,
                                     herramientas=herramientas))


class RepoQueFalla:
    def __getattr__(self, _):
        def falla(*a, **k):
            raise RuntimeError("password=secreto host=interno")
        return falla
