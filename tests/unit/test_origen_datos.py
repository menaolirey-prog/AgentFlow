"""Regresión: las cifras de las herramientas declaran su origen (es_demo) y el agente no las presenta como reales."""
from datetime import date
from decimal import Decimal

import pytest

from agentflow.agent.prompts import construir_prompt_sistema
from agentflow.agent.render import plantilla_respaldo
from agentflow.agent.verifier import verificar_respuesta
from agentflow.db.repositories.ventas import ResumenVentas
from agentflow.tools.registry import RegistroHerramientas
from tests.fakes import HOY, RepoFalso

PRODUCTOS = [("Laptop", 5, Decimal("5000.00"))]


@pytest.mark.parametrize("origenes,esperado", [
    ((True, False), "demo"), ((False, True), "real"), ((True, True), "mixto"), ((False, False), "sin_ventas")])
@pytest.mark.parametrize("herramienta,args", [
    ("ventas_totales", '{"periodo": "este_mes"}'),
    ("ventas_por_producto", '{"periodo": "este_mes"}'),
    ("comparar_periodos", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}'),
    ("productos_en_caida", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}'),
])
def test_cada_herramienta_rotula_el_origen(herramienta, args, origenes, esperado):
    repo = RepoFalso(productos=PRODUCTOS, resumen=ResumenVentas(Decimal("10"), 1, 1), origenes=origenes)
    r = RegistroHerramientas(repo).ejecutar(herramienta, args, HOY)
    assert r.ok and r.datos["origen_datos"] == esperado


def test_comparacion_une_el_origen_de_ambos_periodos():
    class RepoPorRango(RepoFalso):
        def origenes(self, inicio, fin_exclusivo):
            return (True, False) if inicio.month == 11 else (False, True)
    r = RegistroHerramientas(RepoPorRango(resumen=ResumenVentas(Decimal("10"), 1, 1))).ejecutar(
        "comparar_periodos", '{"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}', HOY)
    assert r.datos["origen_datos"] == "mixto"


def test_plantilla_de_respaldo_rotula_datos_demo():
    repo = RepoFalso(resumen=ResumenVentas(Decimal("10"), 1, 1))
    r = RegistroHerramientas(repo).ejecutar("ventas_totales", '{"periodo": "este_mes"}', HOY)
    assert "DEMO (ficticios, no son ventas reales)" in plantilla_respaldo([r])


def test_el_prompt_prohibe_llamar_reales_a_los_datos_demo():
    p = construir_prompt_sistema(HOY)
    assert "origen_datos" in p and "NUNCA los llames reales" in p


# ---- verificador: formatos reales de Markdown y fecha de hoy ----
DATOS = [{"argumentos": {"periodo": "mes_anterior"}, "datos": {
    "periodo": {"inicio": "2026-09-01", "fin": "2026-09-30"}, "ingresos_totales": 6850.5, "unidades": 29,
    "productos": [{"producto": "Laptop", "unidades": 5, "ingresos": 5000.0}]}}]


@pytest.mark.parametrize("markdown", [
    "| Producto | Unidades | Ingresos |\n|---|---:|---:|\n| Laptop | 5 | S/ 5,000.00 |",
    "**Total:** **S/ 6,850.50** en **29** unidades.",
    "1. **Laptop**: S/ 5,000.00\n2. Otro",
    "### Resumen de septiembre 2026\n- Laptop: 5 unidades",
])
def test_markdown_con_cifras_respaldadas_se_verifica(markdown):
    assert verificar_respuesta(markdown, DATOS, HOY).ok


def test_fecha_de_hoy_respalda_su_dia_sin_debilitar_el_resto():
    texto_hoy = "Al 10 de noviembre de 2026 septiembre sumó S/ 6,850.50."
    assert not verificar_respuesta(texto_hoy, DATOS).ok          # sin hoy: el "10" no está en los datos
    assert verificar_respuesta(texto_hoy, DATOS, HOY).ok         # con hoy: la fecha del sistema es de confianza
    assert not verificar_respuesta("Sumó S/ 6,851.50.", DATOS, HOY).ok   # una cifra inventada sigue fallando
    assert not verificar_respuesta("Sumó 12,5 unidades.", DATOS, HOY).ok  # formato ambiguo sigue fallando


# ---- tres escenarios que no deben confundirse: sin datos / solo demo / sin caídas ----
ARGS_CAIDA = '{"periodo_actual": "2026-10-01/2026-10-31", "periodo_anterior": "2026-09-01/2026-09-30"}'


def _caida(repo):
    return RegistroHerramientas(repo).ejecutar("productos_en_caida", ARGS_CAIDA, HOY)


def test_sin_datos_no_se_confunde_con_sin_caidas():
    r = _caida(RepoFalso(caidas=[], origenes=(False, False)))
    texto_ = plantilla_respaldo([r])
    assert r.datos["origen_datos"] == "sin_ventas" and r.datos["productos"] == []
    assert "No hay datos" in texto_ and "Ningún producto registró caída" not in texto_


def test_solo_demo_es_analizable_y_se_rotula():
    caidas = [("Laptop", Decimal("1000"), Decimal("1500"))]
    r = _caida(RepoFalso(caidas=caidas, origenes=(True, False)))   # el repo no excluye es_demo: solo demo existe
    texto_ = plantilla_respaldo([r])
    assert r.datos["origen_datos"] == "demo" and r.datos["productos"][0]["producto"] == "Laptop"
    assert "Laptop" in texto_ and "DEMO (ficticios" in texto_ and "No hay datos" not in texto_


def test_hay_datos_pero_ningun_producto_cayo():
    r = _caida(RepoFalso(caidas=[], origenes=(True, False)))
    texto_ = plantilla_respaldo([r])
    assert r.datos["origen_datos"] == "demo" and r.datos["productos"] == []
    assert "Ningún producto registró caída" in texto_ and "No hay datos" not in texto_


def test_el_prompt_pide_el_anio_actual_y_distingue_los_tres_casos():
    p = construir_prompt_sistema(HOY)
    assert "usa el año actual" in p and "'sin_ventas' = no hay datos" in p and "analízalas" in p


def test_la_consulta_sql_no_excluye_ventas_demo():
    import inspect
    from agentflow.db.repositories.ventas import RepositorioVentas
    for metodo in (RepositorioVentas.resumen, RepositorioVentas.por_producto, RepositorioVentas.caidas):
        assert "es_demo" not in inspect.getsource(metodo)
