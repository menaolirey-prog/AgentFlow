
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion():
    """Crea una conexión a PostgreSQL."""

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )
