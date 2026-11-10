"""Historial de conversaciones en PostgreSQL. Cada consulta filtra por conversacion_id (parametrizado)."""
from typing import Callable

from agentflow.db.connection import obtener_conexion_escritura

ROLES = ("user", "assistant")
MAX_CHARS = 20000  # igual que el CHECK de la tabla; el texto más largo se recorta


class HistorialPostgres:
    def __init__(self, fabrica_conexion: Callable = obtener_conexion_escritura):
        self._fabrica = fabrica_conexion

    def crear(self) -> str:
        with self._fabrica() as conexion:
            fila = conexion.execute("INSERT INTO conversaciones DEFAULT VALUES RETURNING id").fetchone()
        return str(fila[0])

    def agregar(self, conversacion_id: str, mensajes: list[tuple[str, str]]) -> None:
        """Inserta varios mensajes en una sola transacción (todo o nada)."""
        for rol, contenido in mensajes:
            if rol not in ROLES:
                raise ValueError(f"rol inválido: {rol!r}")
        filas = [(conversacion_id, rol, contenido[:MAX_CHARS]) for rol, contenido in mensajes]
        with self._fabrica() as conexion:
            with conexion.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO mensajes (conversacion_id, rol, contenido) VALUES (%s, %s, %s)", filas)

    def cargar(self, conversacion_id: str, limite: int) -> list[dict] | None:
        """Últimos `limite` mensajes en orden cronológico; None si la conversación no existe."""
        with self._fabrica() as conexion:
            if conexion.execute("SELECT 1 FROM conversaciones WHERE id = %s", (conversacion_id,)).fetchone() is None:
                return None
            filas = conexion.execute(
                """SELECT rol, contenido FROM (
                       SELECT id, rol, contenido FROM mensajes
                       WHERE conversacion_id = %s ORDER BY id DESC LIMIT %s) ultimos
                   ORDER BY id""", (conversacion_id, limite)).fetchall()
        return [{"role": rol, "content": contenido} for rol, contenido in filas]

    def listar(self, limite: int = 10) -> list[dict]:
        with self._fabrica() as conexion:
            filas = conexion.execute(
                """SELECT c.id, c.creada_en, COUNT(m.id),
                          (SELECT left(contenido, 60) FROM mensajes
                           WHERE conversacion_id = c.id AND rol = 'user' ORDER BY id LIMIT 1)
                   FROM conversaciones c LEFT JOIN mensajes m ON m.conversacion_id = c.id
                   GROUP BY c.id, c.creada_en
                   ORDER BY c.creada_en DESC LIMIT %s""", (limite,)).fetchall()
        return [{"id": str(i), "creada_en": t, "mensajes": int(n), "inicio": ini} for i, t, n, ini in filas]
