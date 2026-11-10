"""Conexiones con el rol de la aplicación (agentflow_app, permisos mínimos). Nunca el administrador."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def _conectar(timeout_sentencia_ms: int) -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
        options=f"-c statement_timeout={int(timeout_sentencia_ms)}",
    )


def obtener_conexion_lectura(timeout_sentencia_ms: int = 5000) -> psycopg.Connection:
    conexion = _conectar(timeout_sentencia_ms)
    conexion.read_only = True  # defensa adicional al GRANT SELECT del rol
    return conexion


def obtener_conexion_escritura(timeout_sentencia_ms: int = 5000) -> psycopg.Connection:
    """Solo para el historial. `with` confirma (commit) al salir sin error y cierra la conexión.
    Lo que se pueda escribir lo limita el GRANT de cada tabla, no este código."""
    return _conectar(timeout_sentencia_ms)
