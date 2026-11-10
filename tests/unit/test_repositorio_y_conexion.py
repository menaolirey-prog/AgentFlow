from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from agentflow.db import connection
from agentflow.db.repositories.ventas import RepositorioVentas


def _repo(filas):
    conexion = MagicMock()
    conexion.__enter__.return_value = conexion
    cursor = conexion.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = filas
    return RepositorioVentas(lambda: conexion), cursor


def test_resumen_parametriza_fechas_y_convierte_tipos():
    repo, cursor = _repo([(Decimal("10.50"), 3, 2)])
    r = repo.resumen(date(2026, 11, 1), date(2026, 11, 11))
    sql, params = cursor.execute.call_args.args
    assert params == (date(2026, 11, 1), date(2026, 11, 11))
    assert "precio_unitario" in sql and "p.precio" not in sql  # ingresos históricos
    assert (r.ingresos, r.unidades, r.n_ventas) == (Decimal("10.50"), 3, 2)


def test_por_producto_orden_desde_mapa_cerrado():
    repo, cursor = _repo([])
    repo.por_producto(date(2026, 1, 1), date(2026, 2, 1), "unidades", 5)
    sql, params = cursor.execute.call_args.args
    assert "ORDER BY unidades DESC" in sql and params[-1] == 5
    with pytest.raises(KeyError):
        repo.por_producto(date(2026, 1, 1), date(2026, 2, 1), "nombre; DROP TABLE ventas", 5)


def test_caidas_usa_parametros_con_nombre():
    repo, cursor = _repo([])
    repo.caidas((date(2026, 11, 1), date(2026, 11, 11)), (date(2026, 10, 1), date(2026, 11, 1)), 3)
    _, params = cursor.execute.call_args.args
    assert params["limite"] == 3 and params["b_ini"] == date(2026, 10, 1)


def test_conexion_es_de_solo_lectura_con_timeout():
    with patch.object(connection.psycopg, "connect") as conectar:
        conexion = connection.obtener_conexion_lectura(1500)
    assert conexion.read_only is True
    assert conectar.call_args.kwargs["options"] == "-c statement_timeout=1500"
    assert conectar.call_args.kwargs["connect_timeout"] == 5
