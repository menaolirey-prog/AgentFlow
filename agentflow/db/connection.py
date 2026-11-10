"""Conexión de SOLO LECTURA con timeout de sentencia."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion_lectura(timeout_sentencia_ms: int = 5000) -> psycopg.Connection:
    conexion = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
        options=f"-c statement_timeout={int(timeout_sentencia_ms)}",
    )
    conexion.read_only = True  # defensa adicional al GRANT SELECT del rol
    return conexion
