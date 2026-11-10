from decimal import Decimal
from unittest.mock import patch

import psycopg
import pytest

from herramientas import consultar_ventas


def _configurar_cursor(mock_obtener, filas):
    """Configura el mock para que cursor.fetchall() devuelva `filas`."""
    conexion = mock_obtener.return_value.__enter__.return_value
    cursor = conexion.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = filas
    return cursor


@patch("herramientas.obtener_conexion")
def test_resultado_correcto(mock_obtener):
    # PostgreSQL devuelve Decimal en columnas NUMERIC
    cursor = _configurar_cursor(mock_obtener, [
        ("Laptop", 2, Decimal("5000.00")),
        ("Teclado", 10, Decimal("1000.00")),
        ("Mouse", 17, Decimal("850.00")),
    ])

    resultado = consultar_ventas()

    cursor.execute.assert_called_once()
    assert resultado == {
        "moneda": "PEN",
        "ingresos_totales": 6850.0,
        "producto_lider": "Laptop",
        "ingresos_por_producto": {
            "Laptop": 5000.0,
            "Teclado": 1000.0,
            "Mouse": 850.0,
        },
    }
    assert all(isinstance(v, float) for v in resultado["ingresos_por_producto"].values())


@patch("herramientas.obtener_conexion")
def test_sin_ventas(mock_obtener):
    _configurar_cursor(mock_obtener, [])

    resultado = consultar_ventas()

    assert resultado == {
        "moneda": "PEN",
        "ingresos_totales": 0,
        "producto_lider": None,
        "ingresos_por_producto": {},
    }


@patch("herramientas.obtener_conexion")
def test_error_de_conexion(mock_obtener):
    mock_obtener.side_effect = psycopg.OperationalError("no se pudo conectar")

    with pytest.raises(psycopg.OperationalError):
        consultar_ventas()


@patch("herramientas.obtener_conexion")
def test_error_en_consulta(mock_obtener):
    cursor = _configurar_cursor(mock_obtener, [])
    cursor.execute.side_effect = psycopg.errors.UndefinedTable("tabla ventas no existe")

    with pytest.raises(psycopg.errors.UndefinedTable):
        consultar_ventas()
