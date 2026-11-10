"""Requiere PostgreSQL local con las migraciones aplicadas. Ejecutar: pytest -m integration"""
import pytest

from agentflow.db.connection import obtener_conexion_lectura
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.tools.registry import RegistroHerramientas
from tests.fakes import HOY

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def registro():
    return RegistroHerramientas(RepositorioVentas())


def test_la_conexion_no_puede_escribir():
    import psycopg
    with obtener_conexion_lectura() as c:
        with pytest.raises(psycopg.Error):
            c.execute("INSERT INTO ventas (id_producto, cantidad, fecha, precio_unitario) "
                      "VALUES (1, 1, now(), 1)")


def test_totales_coinciden_con_el_ranking(registro):
    r = "2026-05-01/2026-10-31"
    total = registro.ejecutar("ventas_totales", f'{{"periodo": "{r}"}}', HOY).datos
    ranking = registro.ejecutar("ventas_por_producto", f'{{"periodo": "{r}", "limite": 50}}', HOY).datos
    assert total["ingresos_totales"] == pytest.approx(sum(p["ingresos"] for p in ranking["productos"]))
    assert total["unidades"] == sum(p["unidades"] for p in ranking["productos"])


def test_el_mouse_cae_en_octubre_segun_los_datos_demo(registro):
    d = registro.ejecutar("productos_en_caida", '{"periodo_actual": "2026-10-01/2026-10-31", '
                          '"periodo_anterior": "2026-09-01/2026-09-30"}', HOY)
    assert d.ok and "Mouse" in [p["producto"] for p in d.datos["productos"]]


def test_comparacion_mes_a_mes_ejecuta(registro):
    d = registro.ejecutar("comparar_periodos", '{"periodo_actual": "mes_anterior", '
                          '"periodo_anterior": "2026-09-01/2026-09-30"}', HOY)
    assert d.ok and d.datos["anterior"]["ingresos"] > 0
