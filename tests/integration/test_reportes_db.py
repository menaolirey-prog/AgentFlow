"""Reportes contra PostgreSQL local (solo lectura) + cierre de ejecuciones interrumpidas (transacción revertida)."""
import pytest

from agentflow.db.connection import obtener_conexion_escritura, obtener_conexion_lectura
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.tools.registry import RegistroHerramientas
from agentflow.tools.reportes import construir_reporte
from tests.fakes import HOY

pytestmark = pytest.mark.integration


def test_reporte_coincide_con_ventas_totales_y_se_reparte_por_origen():
    repo = RepositorioVentas()
    periodo = "2026-05-01/2026-11-10"
    r = construir_reporte(repo, periodo, None, "todos", HOY)
    total = RegistroHerramientas(repo).ejecutar("ventas_totales", f'{{"periodo": "{periodo}"}}', HOY).datos
    assert r["total_combinado"]["ingresos"] == pytest.approx(total["ingresos_totales"])
    assert r["total_combinado"]["unidades"] == total["unidades"]
    assert sum(s["total"]["ingresos"] for s in r["origenes"].values()) == pytest.approx(total["ingresos_totales"])
    assert r["contiene_datos_demo"] is True


def test_origen_demo_coincide_con_sql_directo():
    r = construir_reporte(RepositorioVentas(), "2026-05-01/2026-11-10", None, "demo", HOY)
    with obtener_conexion_lectura() as c:
        ingresos, unidades = c.execute(
            "SELECT SUM(cantidad * precio_unitario), SUM(cantidad) FROM ventas WHERE es_demo "
            "AND fecha >= '2026-05-01' AND fecha < '2026-11-11'").fetchone()
    assert r["origenes"]["demo"]["total"]["ingresos"] == pytest.approx(float(ingresos))
    assert r["origenes"]["demo"]["total"]["unidades"] == unidades
    assert list(r["origenes"]) == ["demo"]


def test_el_mouse_cae_en_octubre_en_el_reporte_comparativo():
    r = construir_reporte(RepositorioVentas(), "2026-10-01/2026-10-31", "2026-09-01/2026-09-30", "demo", HOY)
    mouse = next(p for p in r["origenes"]["demo"]["productos"] if p["producto"] == "Mouse")
    assert mouse["variacion_pct"] == -37.5 and mouse["ingresos_anterior"] == 800.0


class _SinCommit:
    def __init__(self, c):
        self._c = c

    def __enter__(self):
        return self._c

    def __exit__(self, *a):
        return False


def test_cerrar_interrumpidas_solo_cierra_las_antiguas():
    c = obtener_conexion_escritura()
    try:
        if c.execute("SELECT to_regclass('public.ejecuciones')").fetchone()[0] is None:
            pytest.skip("migración 005 sin aplicar")
        vieja = c.execute("INSERT INTO ejecuciones (pregunta_chars, iniciada_en) "
                          "VALUES (1, now() - interval '1 hour') RETURNING id").fetchone()[0]
        reciente = c.execute("INSERT INTO ejecuciones (pregunta_chars) VALUES (1) RETURNING id").fetchone()[0]
        cerradas = RegistroEjecuciones(lambda: _SinCommit(c)).cerrar_interrumpidas(5)
        assert str(vieja) in cerradas and str(reciente) not in cerradas
        assert c.execute("SELECT estado, motivo FROM ejecuciones WHERE id = %s", (vieja,)).fetchone() == (
            "error", "interrumpida")
        assert c.execute("SELECT estado FROM ejecuciones WHERE id = %s", (reciente,)).fetchone()[0] == "en_curso"
    finally:
        c.rollback()
        c.close()


def test_periodo_sin_ventas_reales_separa_todo_como_demo():
    """2026-05..10 solo contiene ventas demo (las 3 iniciales son de 2026-11-10)."""
    r = construir_reporte(RepositorioVentas(), "2026-05-01/2026-10-31", None, "todos", HOY)
    assert r["origenes"]["real"]["total"]["numero_ventas"] == 0 and r["origenes"]["real"]["productos"] == []
    assert r["origenes"]["demo"]["total"]["ingresos"] == r["total_combinado"]["ingresos"] > 0


def test_tras_la_migracion_006_todo_el_historial_es_demo():
    with obtener_conexion_lectura() as c:
        reales = c.execute("SELECT count(*) FROM ventas WHERE NOT es_demo").fetchone()[0]
    if reales:
        pytest.skip("migración 006 sin aplicar")
    r = construir_reporte(RepositorioVentas(), "este_anio", None, "real", HOY)
    assert r["total_combinado"]["numero_ventas"] == 0 and r["producto_lider"] is None
