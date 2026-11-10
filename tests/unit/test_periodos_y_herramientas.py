from datetime import date
from decimal import Decimal

import pytest

from agentflow.db.repositories.ventas import ResumenVentas
from agentflow.tools.periodos import resolver_periodo
from agentflow.tools.registry import MENSAJE_ERROR_INTERNO, RegistroHerramientas
from tests.fakes import HOY, RepoFalso, RepoQueFalla


# ---- periodos: las fechas las calcula el código ----
@pytest.mark.parametrize("texto,inicio,fin", [
    ("este_mes", date(2026, 11, 1), date(2026, 11, 10)),
    ("mes_anterior", date(2026, 10, 1), date(2026, 10, 31)),
    ("ultimos_7_dias", date(2026, 11, 4), date(2026, 11, 10)),
    ("ultimos_30_dias", date(2026, 10, 12), date(2026, 11, 10)),
    ("este_anio", date(2026, 1, 1), date(2026, 11, 10)),
    ("2026-09-01/2026-09-30", date(2026, 9, 1), date(2026, 9, 30)),
    ("2026-11-01/2026-12-31", date(2026, 11, 1), date(2026, 11, 10)),  # fin futuro se recorta a hoy
])
def test_resolver_periodo(texto, inicio, fin):
    p = resolver_periodo(texto, HOY)
    assert (p.inicio, p.fin) == (inicio, fin)


def test_mes_anterior_en_enero_cruza_de_anio():
    p = resolver_periodo("mes_anterior", date(2026, 1, 15))
    assert (p.inicio, p.fin) == (date(2025, 12, 1), date(2025, 12, 31))


@pytest.mark.parametrize("texto", ["ayer", "2026-13-01/2026-13-02", "2026-02-30/2026-03-01",
                                   "2026-10-05/2026-10-01", "2026-12-01/2026-12-31",
                                   "2020-01-01/2026-11-10", "' OR 1=1 --"])
def test_periodo_invalido(texto):
    with pytest.raises(ValueError):
        resolver_periodo(texto, HOY)


# ---- registro: validación y autorización ----
@pytest.fixture
def registro():
    return RegistroHerramientas(RepoFalso())


def test_esquemas_sin_titulos_y_sin_campos_extra(registro):
    esquemas = registro.esquemas()
    assert [e["function"]["name"] for e in esquemas] == [
        "ventas_totales", "ventas_por_producto", "comparar_periodos", "productos_en_caida"]
    for e in esquemas:
        assert "title" not in str(e["function"]["parameters"])
        assert e["function"]["parameters"]["additionalProperties"] is False


def test_herramienta_no_registrada_se_rechaza(registro):
    r = registro.ejecutar("ejecutar_sql", '{"sql": "DROP TABLE ventas"}', HOY)
    assert not r.ok and r.codigo_error == "herramienta_no_autorizada"


@pytest.mark.parametrize("nombre,args", [
    ("ventas_totales", '{"periodo": "este_mes", "sql": "SELECT 1"}'),            # campo no declarado
    ("ventas_totales", '{"periodo": "1; DROP TABLE ventas"}'),                    # periodo mal formado
    ("ventas_totales", "no es json"),
    ("ventas_totales", "[1, 2]"),
    ("ventas_totales", "{}"),                                                     # falta periodo
    ("ventas_por_producto", '{"periodo": "este_mes", "limite": 0}'),
    ("ventas_por_producto", '{"periodo": "este_mes", "limite": 1000}'),
    ("ventas_por_producto", '{"periodo": "este_mes", "ordenar_por": "nombre; DROP TABLE x"}'),
    ("comparar_periodos", '{"periodo_actual": "este_mes"}'),
])
def test_argumentos_invalidos_no_llegan_al_repositorio(nombre, args):
    repo = RepoFalso()
    r = RegistroHerramientas(repo).ejecutar(nombre, args, HOY)
    assert not r.ok and r.codigo_error == "argumentos_invalidos"
    assert repo.llamadas == []


def test_periodo_imposible_es_argumento_invalido():
    r = RegistroHerramientas(RepoFalso()).ejecutar(
        "ventas_totales", '{"periodo": "2026-12-01/2026-12-31"}', HOY)
    assert r.codigo_error == "argumentos_invalidos"


def test_error_interno_no_filtra_detalles():
    r = RegistroHerramientas(RepoQueFalla()).ejecutar("ventas_totales", '{"periodo": "este_mes"}', HOY)
    assert not r.ok and r.codigo_error == "error_interno"
    assert r.datos["mensaje"] == MENSAJE_ERROR_INTERNO
    assert "password" not in r.contenido() and "host=" not in r.contenido()


# ---- herramientas: cálculo determinista ----
def test_ventas_totales():
    repo = RepoFalso(resumen=ResumenVentas(Decimal("6850.50"), 29, 12))
    r = RegistroHerramientas(repo).ejecutar("ventas_totales", '{"periodo": "este_mes"}', HOY)
    assert r.ok and r.datos == {
        "moneda": "PEN", "periodo": {"inicio": "2026-11-01", "fin": "2026-11-10"},
        "ingresos_totales": 6850.5, "unidades": 29, "numero_ventas": 12}
    assert repo.llamadas == [("resumen", date(2026, 11, 1), date(2026, 11, 11))]  # fin exclusivo


def test_ventas_por_producto_usa_argumentos_validados():
    repo = RepoFalso(productos=[("Laptop", 3, Decimal("9000")), ("Mouse", 5, Decimal("100.5"))])
    r = RegistroHerramientas(repo).ejecutar(
        "ventas_por_producto", '{"periodo": "mes_anterior", "ordenar_por": "unidades", "limite": 2}', HOY)
    assert r.datos["productos"][1] == {"producto": "Mouse", "unidades": 5, "ingresos": 100.5}
    assert repo.llamadas == [("por_producto", date(2026, 10, 1), date(2026, 11, 1), "unidades", 2)]


def test_comparar_periodos_calcula_variaciones():
    repo = RepoFalso(resumen=[ResumenVentas(Decimal("900"), 9, 3), ResumenVentas(Decimal("1200"), 12, 4)])
    d = RegistroHerramientas(repo).ejecutar(
        "comparar_periodos", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}', HOY).datos
    assert d["variacion_ingresos"] == -300.0 and d["variacion_ingresos_pct"] == -25.0
    assert d["variacion_unidades"] == -3 and d["variacion_unidades_pct"] == -25.0


def test_comparar_con_base_cero_no_divide():
    repo = RepoFalso(resumen=[ResumenVentas(Decimal("500"), 5, 1), ResumenVentas(Decimal("0"), 0, 0)])
    d = RegistroHerramientas(repo).ejecutar(
        "comparar_periodos", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}', HOY).datos
    assert d["variacion_ingresos_pct"] is None and d["variacion_unidades_pct"] is None


def test_productos_en_caida():
    repo = RepoFalso(caidas=[("Mouse", Decimal("100"), Decimal("400"))])
    d = RegistroHerramientas(repo).ejecutar(
        "productos_en_caida", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}', HOY).datos
    assert d["productos"] == [{"producto": "Mouse", "ingresos_actual": 100.0, "ingresos_anterior": 400.0,
                               "caida": 300.0, "variacion_pct": -75.0}]
    nombre, actual, anterior, limite = repo.llamadas[0]
    assert actual == (date(2026, 11, 1), date(2026, 11, 11)) and limite == 5


def test_plantilla_es_imprimible_en_consola_windows():
    from agentflow.agent.render import plantilla_respaldo
    repo = RepoFalso(caidas=[("Mouse", Decimal("100"), Decimal("400"))],
                     productos=[("Laptop", 3, Decimal("9000"))])
    reg = RegistroHerramientas(repo)
    rs = [reg.ejecutar("productos_en_caida", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}', HOY),
          reg.ejecutar("ventas_por_producto", '{"periodo": "este_mes"}', HOY)]
    plantilla_respaldo(rs).encode("cp1252")  # no debe lanzar UnicodeEncodeError
