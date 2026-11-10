"""Registro persistente de ejecuciones. Nunca guarda texto de preguntas/respuestas ni mensajes de error."""
from typing import Callable

from psycopg.types.json import Jsonb

from agentflow.db.connection import obtener_conexion_escritura

ESTADOS_FINALES = ("ok", "degradado", "limite", "error")
ORIGENES = ("modelo", "plantilla", "mensaje_error")
_MAX_TEXTO = 60  # igual que los CHECK de la tabla


def _corto(valor: str | None) -> str | None:
    return None if valor is None else valor[:_MAX_TEXTO]


class RegistroEjecuciones:
    def __init__(self, fabrica_conexion: Callable = obtener_conexion_escritura):
        self._fabrica = fabrica_conexion

    def iniciar(self, conversacion_id: str | None, pregunta_chars: int) -> str:
        with self._fabrica() as conexion:
            fila = conexion.execute(
                "INSERT INTO ejecuciones (conversacion_id, pregunta_chars) VALUES (%s, %s) RETURNING id",
                (conversacion_id, pregunta_chars)).fetchone()
        return str(fila[0])

    def finalizar(self, ejecucion_id: str, estado: str, motivo: str | None, origen: str,
                  tokens_entrada: int, tokens_salida: int, llamadas_llm: int, duracion_ms: int,
                  herramientas: list[dict]) -> None:
        """Cierra la ejecución y guarda sus herramientas en una sola transacción."""
        if estado not in ESTADOS_FINALES:
            raise ValueError(f"estado final inválido: {estado!r}")
        if origen not in ORIGENES:
            raise ValueError(f"origen inválido: {origen!r}")
        filas = [(ejecucion_id, orden, _corto(h["nombre"]),
                  None if h["argumentos"] is None else Jsonb(h["argumentos"]),
                  h["ok"], _corto(h["codigo_error"]), h["duracion_ms"])
                 for orden, h in enumerate(herramientas, start=1)]
        with self._fabrica() as conexion:
            actualizadas = conexion.execute(
                """UPDATE ejecuciones
                   SET estado = %s, motivo = %s, origen = %s, tokens_entrada = %s, tokens_salida = %s,
                       llamadas_llm = %s, duracion_ms = %s, finalizada_en = now()
                   WHERE id = %s AND estado = 'en_curso'""",
                (estado, _corto(motivo), origen, tokens_entrada, tokens_salida, llamadas_llm, duracion_ms,
                 ejecucion_id)).rowcount
            if actualizadas != 1:
                raise LookupError("ejecución inexistente o ya finalizada")  # revierte: no quedan herramientas sueltas
            if filas:
                with conexion.cursor() as cursor:
                    cursor.executemany(
                        """INSERT INTO ejecucion_herramientas
                           (ejecucion_id, orden, herramienta, argumentos, ok, codigo_error, duracion_ms)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""", filas)

    def cerrar_interrumpidas(self, antiguedad_minutos: int = 5) -> list[str]:
        """Marca como error/'interrumpida' las ejecuciones 'en_curso' más antiguas que el umbral.

        Una solicitud dura como máximo ~30-50 s (Limites), así que 5 min en 'en_curso' solo se explica por un
        proceso interrumpido. El desenlace real (¿se entregó respuesta?) es DESCONOCIDO; el motivo lo deja explícito.
        La app puede hacerlo: el GRANT cubre estas columnas y el trigger solo permite tocar filas 'en_curso'."""
        if antiguedad_minutos < 1:
            raise ValueError("el umbral debe ser de al menos 1 minuto")
        with self._fabrica() as conexion:
            filas = conexion.execute(
                """UPDATE ejecuciones SET estado = 'error', motivo = 'interrumpida', finalizada_en = now()
                   WHERE estado = 'en_curso' AND iniciada_en < now() - make_interval(mins => %s)
                   RETURNING id""", (antiguedad_minutos,)).fetchall()
        return [str(f[0]) for f in filas]

    def listar(self, conversacion_id: str | None = None, limite: int = 10) -> list[dict]:
        """Ejecuciones recientes (de una sesión o de todas), con número de herramientas."""
        with self._fabrica() as conexion:
            filas = conexion.execute(
                """SELECT e.id, e.estado, e.motivo, e.origen, e.tokens_entrada + e.tokens_salida,
                          e.duracion_ms, e.iniciada_en, COUNT(h.id)
                   FROM ejecuciones e LEFT JOIN ejecucion_herramientas h ON h.ejecucion_id = e.id
                   WHERE (%s::uuid IS NULL OR e.conversacion_id = %s::uuid)
                   GROUP BY e.id ORDER BY e.iniciada_en DESC LIMIT %s""",
                (conversacion_id, conversacion_id, limite)).fetchall()
        return [{"id": str(i), "estado": est, "motivo": mot, "origen": ori, "tokens": tok, "duracion_ms": dur,
                 "iniciada_en": ini, "herramientas": int(n)} for i, est, mot, ori, tok, dur, ini, n in filas]

    def detalle(self, ejecucion_id: str) -> dict | None:
        """Ejecución con sus herramientas (solo metadatos: IDs, códigos, duraciones). None si no existe."""
        with self._fabrica() as conexion:
            fila = conexion.execute(
                """SELECT id, conversacion_id, estado, motivo, origen, pregunta_chars, tokens_entrada, tokens_salida,
                          llamadas_llm, duracion_ms, iniciada_en, finalizada_en
                   FROM ejecuciones WHERE id = %s""", (ejecucion_id,)).fetchone()
            if fila is None:
                return None
            herramientas = conexion.execute(
                """SELECT orden, herramienta, argumentos, ok, codigo_error, duracion_ms
                   FROM ejecucion_herramientas WHERE ejecucion_id = %s ORDER BY orden""", (ejecucion_id,)).fetchall()
        i, conv, est, mot, ori, pch, tin, tout, llm, dur, ini, fin = fila
        return {"id": str(i), "conversacion_id": None if conv is None else str(conv), "estado": est, "motivo": mot,
                "origen": ori, "pregunta_chars": pch, "tokens_entrada": tin, "tokens_salida": tout,
                "llamadas_llm": llm, "duracion_ms": dur, "iniciada_en": ini, "finalizada_en": fin,
                "herramientas": [{"orden": o, "herramienta": h, "argumentos": a, "ok": ok, "codigo_error": c,
                                  "duracion_ms": d} for o, h, a, ok, c, d in herramientas]}
