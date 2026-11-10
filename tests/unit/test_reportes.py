import csv
import io
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from agentflow.agent.render import formatear_reporte, plantilla_respaldo
from agentflow.agent.verifier import verificar_respuesta
from agentflow.cli import ejecutar_reporte, parsear_reporte
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.tools.registry import RegistroHerramientas
from agentflow.tools.reportes import COLUMNAS_CSV, construir_reporte, escribir_csv, guardar_csv
from tests.fakes import HOY, RepoFalso

# (es_demo, producto, unidades, ingresos, n_ventas)
ACTUAL = [(False, "Laptop", 1, Decimal("5000"), 1), (False, "Mouse", 3, Decimal("150"), 1),
          (True, "Laptop", 2, Decimal("10000"), 2), (True, "Monitor", 4, Decimal("1600"), 4)]
ANTERIOR = [(False, "Laptop", 1, Decimal("4000"), 1), (False, "Teclado", 2, Decimal("200"), 1),
            (True, "Laptop", 1, Decimal("5000"), 1)]


def _reporte(origen="todos", comparar=None, actual=ACTUAL, anterior=ANTERIOR):
    filas = [list(actual), list(anterior)] if comparar else list(actual)
    repo = RepoFalso(origen_filas=filas)
    return construir_reporte(repo, "este_mes", comparar, origen, HOY), repo


# ---- separación demo / real ----
def test_secciones_real_y_demo_separadas_con_total_combinado_explicito():
    r, _ = _reporte()
    assert r["origenes"]["real"]["total"] == {"ingresos": 5150.0, "unidades": 4, "numero_ventas": 2}
    assert r["origenes"]["demo"]["total"] == {"ingresos": 11600.0, "unidades": 6, "numero_ventas": 6}
    assert r["total_combinado"]["ingresos"] == 16750.0 and r["total_combinado"]["unidades"] == 10
    assert r["contiene_datos_demo"] is True and "ficticios" in r["advertencia"]
    assert r["producto_lider"] == "Laptop"  # 15,000 combinado
    assert [p["producto"] for p in r["origenes"]["demo"]["productos"]] == ["Laptop", "Monitor"]


def test_filtro_real_excluye_demo_y_sin_advertencia():
    r, _ = _reporte(origen="real")
    assert list(r["origenes"]) == ["real"] and r["contiene_datos_demo"] is False and r["advertencia"] is None
    assert r["total_combinado"]["ingresos"] == 5150.0


def test_filtro_demo_solo_demo():
    r, _ = _reporte(origen="demo")
    assert list(r["origenes"]) == ["demo"] and r["total_combinado"]["ingresos"] == 11600.0
    assert r["contiene_datos_demo"] is True


def test_participacion_por_origen():
    r, _ = _reporte()
    assert r["origenes"]["real"]["productos"][0]["participacion_pct"] == pytest.approx(97.1, abs=0.05)


def test_periodo_sin_ventas():
    r, _ = _reporte(actual=[])
    assert r["total_combinado"] == {"ingresos": 0.0, "unidades": 0, "numero_ventas": 0}
    assert r["producto_lider"] is None and r["contiene_datos_demo"] is False
    assert r["origenes"]["real"]["productos"] == []


def test_origen_invalido_se_rechaza_sin_consultar():
    repo = RepoFalso()
    with pytest.raises(ValueError):
        construir_reporte(repo, "este_mes", None, "todo; DROP TABLE ventas", HOY)
    assert repo.llamadas == []


# ---- comparación ----
def test_comparacion_por_origen_con_producto_que_dejo_de_venderse():
    r, repo = _reporte(comparar="mes_anterior")
    real = r["origenes"]["real"]
    assert real["total"]["ingresos_anterior"] == 4200.0
    assert real["total"]["variacion_ingresos"] == 950.0 and real["total"]["variacion_ingresos_pct"] == 22.6
    por = {p["producto"]: p for p in real["productos"]}
    assert por["Teclado"]["ingresos"] == 0.0 and por["Teclado"]["variacion_pct"] == -100.0  # existía antes
    assert por["Mouse"]["ingresos_anterior"] == 0.0 and por["Mouse"]["variacion_pct"] is None  # base cero
    assert r["periodo_anterior"] == {"inicio": "2026-10-01", "fin": "2026-10-31"}
    assert [c[0] for c in repo.llamadas] == ["por_origen_producto"] * 2


def test_total_combinado_de_comparacion_es_la_suma_de_secciones():
    r, _ = _reporte(comparar="mes_anterior")
    suma = sum(r["origenes"][o]["total"]["variacion_ingresos"] for o in ("real", "demo"))
    assert r["total_combinado"]["variacion_ingresos"] == pytest.approx(suma)


# ---- herramienta del agente y plantilla ----
def test_herramienta_reporte_ventas_valida_argumentos_y_calcula():
    repo = RepoFalso(origen_filas=list(ACTUAL))
    reg = RegistroHerramientas(repo)
    ok = reg.ejecutar("reporte_ventas", '{"periodo": "este_mes"}', HOY)
    assert ok.ok and ok.argumentos == {"periodo": "este_mes", "comparar_con": "", "origen": "todos"}
    for malo in ('{"periodo": "este_mes", "origen": "todo"}', '{"periodo": "este_mes", "comparar_con": "ayer"}',
                 '{"periodo": "este_mes", "sql": "x"}'):
        r = reg.ejecutar("reporte_ventas", malo, HOY)
        assert not r.ok and r.codigo_error == "argumentos_invalidos"
    assert len(repo.llamadas) == 1  # los inválidos no llegaron al repositorio


def test_cifras_del_reporte_son_verificables_y_la_plantilla_rotula_demo():
    reg = RegistroHerramientas(RepoFalso(origen_filas=list(ACTUAL)))
    res = reg.ejecutar("reporte_ventas", '{"periodo": "este_mes"}', HOY)
    ctx = [{"argumentos": res.argumentos, "datos": res.datos}]
    assert verificar_respuesta("Total combinado S/ 16,750.00; demo S/ 11,600.00.", ctx).ok
    assert not verificar_respuesta("Total combinado S/ 17,750.00.", ctx).ok
    texto = plantilla_respaldo([res])
    assert "DATOS DEMO (ficticios)" in texto and "DATOS REALES" in texto and "TOTAL COMBINADO" in texto
    texto.encode("cp1252")  # imprimible en consola Windows


def test_formatear_reporte_con_comparacion_y_solo_real():
    r, _ = _reporte(origen="real", comparar="mes_anterior")
    texto = formatear_reporte(r)
    assert "frente a 2026-10-01 al 2026-10-31" in texto and "vs anterior" in texto
    assert "DEMO" not in texto and "AVISO" not in texto


def test_sql_del_reporte_agrupa_por_origen_con_parametros():
    conexion = MagicMock()
    conexion.__enter__.return_value = conexion
    cursor = conexion.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    RepositorioVentas(lambda: conexion).por_origen_producto(date(2026, 11, 1), date(2026, 11, 11))
    sql, params = cursor.execute.call_args.args
    assert "GROUP BY v.es_demo" in sql and "precio_unitario" in sql
    assert params == (date(2026, 11, 1), date(2026, 11, 11))


# ---- CSV ----
def _csv(r):
    buf = io.StringIO()
    escribir_csv(r, buf)
    return list(csv.DictReader(io.StringIO(buf.getvalue())))


def test_csv_nunca_omite_el_origen_e_incluye_totales():
    filas = _csv(_reporte()[0])
    assert list(filas[0]) == COLUMNAS_CSV
    assert {f["origen"] for f in filas} == {"real", "demo", "combinado"}
    total_demo = next(f for f in filas if f["origen"] == "demo" and f["producto"] == "TOTAL")
    assert total_demo["ingresos"] == "11600.00" and total_demo["unidades"] == "6"
    assert next(f for f in filas if f["origen"] == "combinado")["ingresos"] == "16750.00"
    assert filas[0]["moneda"] == "PEN" and filas[0]["periodo_inicio"] == "2026-11-01"


def test_csv_con_comparacion_y_filtro_real():
    filas = _csv(_reporte(origen="real", comparar="mes_anterior")[0])
    assert {f["origen"] for f in filas} == {"real"}  # sin fila 'combinado' con un solo origen
    teclado = next(f for f in filas if f["producto"] == "Teclado")
    assert teclado["variacion_pct"] == "-100.0" and teclado["periodo_anterior_inicio"] == "2026-10-01"


def test_csv_neutraliza_inyeccion_de_formulas():
    filas = _csv(_reporte(actual=[(False, "=HYPERLINK(\"http://x\")", 1, Decimal("10"), 1)])[0])
    assert filas[0]["producto"].startswith("'=")


def test_guardar_csv_escribe_con_bom_y_no_sobrescribe(tmp_path):
    r, _ = _reporte()
    ruta = guardar_csv(r, "ventas_nov-2026.csv", tmp_path)
    assert ruta.read_bytes().startswith(b"\xef\xbb\xbf") and ruta.read_text("utf-8-sig").startswith("origen,")
    with pytest.raises(FileExistsError):
        guardar_csv(r, "ventas_nov-2026.csv", tmp_path)


@pytest.mark.parametrize("nombre", ["../fuga.csv", "a/b.csv", "a\\b.csv", "reporte.txt", ".csv", "x" * 70 + ".csv",
                                    "c:evil.csv"])
def test_guardar_csv_rechaza_nombres_peligrosos(nombre, tmp_path):
    with pytest.raises(ValueError):
        guardar_csv(_reporte()[0], nombre, tmp_path)
    assert list(tmp_path.iterdir()) == []


# ---- comando /reporte ----
def test_parsear_reporte():
    assert parsear_reporte("este_mes") == {"periodo": "este_mes", "comparar_con": None, "origen": "todos", "csv": None}
    p = parsear_reporte("este_mes vs mes_anterior --origen real --csv r.csv")
    assert (p["comparar_con"], p["origen"], p["csv"]) == ("mes_anterior", "real", "r.csv")


@pytest.mark.parametrize("texto", ["", "a b", "este_mes vs", "este_mes --origen", "este_mes --origen otro", 'este_mes "'])
def test_parsear_reporte_errores(texto):
    with pytest.raises(ValueError):
        parsear_reporte(texto)


def test_ejecutar_reporte_extremo_a_extremo_con_repo_falso(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    salida = ejecutar_reporte("2026-11-01/2026-11-10 --csv r.csv", RepoFalso(origen_filas=list(ACTUAL)))
    assert "DATOS DEMO" in salida and "CSV guardado" in salida and (tmp_path / "reportes" / "r.csv").exists()


# ---- ejecuciones interrumpidas ----
def _ejec(filas):
    conexion = MagicMock()
    conexion.__enter__.return_value = conexion
    conexion.execute.return_value.fetchall.return_value = filas
    return RegistroEjecuciones(lambda: conexion), conexion


def test_cerrar_interrumpidas_solo_toca_en_curso_antiguas_con_parametros():
    a, b = str(uuid4()), str(uuid4())
    repo, conexion = _ejec([(a,), (b,)])
    assert repo.cerrar_interrumpidas(10) == [a, b]
    sql, params = conexion.execute.call_args.args
    assert "estado = 'en_curso'" in sql and "make_interval" in sql and params == (10,)
    assert "motivo = 'interrumpida'" in sql and "estado = 'error'" in sql


def test_cerrar_interrumpidas_umbral_invalido():
    repo, conexion = _ejec([])
    with pytest.raises(ValueError):
        repo.cerrar_interrumpidas(0)
    conexion.execute.assert_not_called()


# ---- escenario sin ventas reales (todas demo) ----
SOLO_DEMO = [(True, "Laptop", 2, Decimal("10000"), 2), (True, "Monitor", 4, Decimal("1600"), 4)]


def test_sin_ventas_reales_la_seccion_real_queda_en_cero_y_no_se_mezcla():
    r, _ = _reporte(actual=SOLO_DEMO)
    assert r["origenes"]["real"] == {"total": {"ingresos": 0.0, "unidades": 0, "numero_ventas": 0}, "productos": []}
    assert r["origenes"]["demo"]["total"]["ingresos"] == 11600.0
    assert r["total_combinado"]["ingresos"] == 11600.0 and r["contiene_datos_demo"] is True
    texto = formatear_reporte(r)
    assert "DATOS REALES: S/ 0.00" in texto and "sin ventas en el periodo" in texto and "DATOS DEMO" in texto


def test_sin_ventas_reales_el_filtro_real_no_arrastra_demo():
    r, _ = _reporte(origen="real", actual=SOLO_DEMO)
    assert r["total_combinado"]["ingresos"] == 0.0 and r["producto_lider"] is None
    assert r["contiene_datos_demo"] is False and r["advertencia"] is None


def test_sin_ventas_reales_el_csv_conserva_las_filas_por_origen():
    filas = _csv(_reporte(actual=SOLO_DEMO)[0])
    real = [f for f in filas if f["origen"] == "real"]
    assert [(f["producto"], f["ingresos"]) for f in real] == [("TOTAL", "0.00")]
    assert sum(float(f["ingresos"]) for f in filas if f["origen"] == "demo" and f["producto"] != "TOTAL") == 11600.0
