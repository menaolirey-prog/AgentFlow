"""Reportes comerciales deterministas. Todo número sale de SQL/Python; el LLM solo puede citarlos.

Los datos reales y los ficticios (ventas.es_demo) se calculan y se muestran por separado; el total
combinado existe solo como suma explícita de las secciones incluidas.
"""
import csv
import re
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from agentflow.config import MONEDA
from agentflow.tools.periodos import resolver_periodo

ORIGENES = ("real", "demo")
FILTROS_ORIGEN = ("todos", *ORIGENES)
CARPETA_REPORTES = Path("reportes")
_NOMBRE_CSV = re.compile(r"^[\w\-]{1,60}\.csv$")
_CERO = {"unidades": 0, "ingresos": Decimal(0), "ventas": 0}


def _dinero(x) -> float:
    return round(float(x), 2)


def _pct(cambio, base) -> float | None:
    return round(float(cambio) / float(base) * 100, 1) if base else None


def _agrupar(filas) -> dict[str, dict[str, dict]]:
    """filas (es_demo, producto, unidades, ingresos, n) -> {'real': {producto: {...}}, 'demo': {...}}"""
    salida: dict[str, dict[str, dict]] = {"real": {}, "demo": {}}
    for es_demo, nombre, unidades, ingresos, n in filas:
        salida["demo" if es_demo else "real"][nombre] = {
            "unidades": int(unidades), "ingresos": Decimal(ingresos), "ventas": int(n)}
    return salida


def _sumar(productos: dict) -> dict:
    return {"unidades": sum(p["unidades"] for p in productos.values()),
            "ingresos": sum((p["ingresos"] for p in productos.values()), Decimal(0)),
            "ventas": sum(p["ventas"] for p in productos.values())}


def _totales(actual: dict, anterior: dict | None) -> dict:
    a = _sumar(actual)
    total = {"ingresos": _dinero(a["ingresos"]), "unidades": a["unidades"], "numero_ventas": a["ventas"]}
    if anterior is not None:
        b = _sumar(anterior)
        total.update({
            "ingresos_anterior": _dinero(b["ingresos"]), "unidades_anterior": b["unidades"],
            "variacion_ingresos": _dinero(a["ingresos"] - b["ingresos"]),
            "variacion_ingresos_pct": _pct(a["ingresos"] - b["ingresos"], b["ingresos"]),
            "variacion_unidades": a["unidades"] - b["unidades"],
            "variacion_unidades_pct": _pct(a["unidades"] - b["unidades"], b["unidades"])})
    return total


def _productos(actual: dict, anterior: dict | None) -> list[dict]:
    total_ingresos = _sumar(actual)["ingresos"]
    filas = []
    for nombre in set(actual) | set(anterior or {}):  # incluye productos que existían antes y hoy no venden
        a = actual.get(nombre, _CERO)
        fila = {"producto": nombre, "unidades": a["unidades"], "ingresos": _dinero(a["ingresos"]),
                "participacion_pct": _pct(a["ingresos"], total_ingresos)}
        if anterior is not None:
            b = anterior.get(nombre, _CERO)
            fila.update({"unidades_anterior": b["unidades"], "ingresos_anterior": _dinero(b["ingresos"]),
                         "variacion_ingresos": _dinero(a["ingresos"] - b["ingresos"]),
                         "variacion_pct": _pct(a["ingresos"] - b["ingresos"], b["ingresos"])})
        filas.append(fila)
    return sorted(filas, key=lambda f: (-f["ingresos"], f["producto"]))


def _fusionar(secciones: list[dict]) -> dict:
    """Suma productos de varios orígenes (solo para el total combinado)."""
    fusion: dict[str, dict] = {}
    for productos in secciones:
        for nombre, p in productos.items():
            acumulado = fusion.setdefault(nombre, dict(_CERO))
            acumulado["unidades"] += p["unidades"]
            acumulado["ingresos"] += p["ingresos"]
            acumulado["ventas"] += p["ventas"]
    return fusion


def construir_reporte(repo, periodo: str, comparar_con: str | None, origen: str, hoy) -> dict:
    if origen not in FILTROS_ORIGEN:
        raise ValueError(f"origen inválido; use {', '.join(FILTROS_ORIGEN)}")
    act = resolver_periodo(periodo, hoy)
    datos_act = _agrupar(repo.por_origen_producto(act.inicio, act.fin_exclusivo))
    ant = resolver_periodo(comparar_con, hoy) if comparar_con else None
    datos_ant = _agrupar(repo.por_origen_producto(ant.inicio, ant.fin_exclusivo)) if ant else None

    incluidos = ORIGENES if origen == "todos" else (origen,)
    origenes = {}
    for nombre in incluidos:
        a, b = datos_act[nombre], (datos_ant[nombre] if datos_ant else None)
        origenes[nombre] = {"total": _totales(a, b), "productos": _productos(a, b)}

    combinado_act = _fusionar([datos_act[n] for n in incluidos])
    combinado_ant = _fusionar([datos_ant[n] for n in incluidos]) if datos_ant else None
    contiene_demo = "demo" in incluidos and bool(
        datos_act["demo"] or (datos_ant["demo"] if datos_ant else False))
    ranking = _productos(combinado_act, None)
    reporte = {
        "moneda": MONEDA, "periodo": act.como_dict(), "origen_filtro": origen,
        "contiene_datos_demo": contiene_demo,
        "advertencia": ("Incluye datos ficticios de demostración (es_demo)." if contiene_demo else None),
        "origenes": origenes,
        "total_combinado": _totales(combinado_act, combinado_ant),
        "producto_lider": ranking[0]["producto"] if ranking and ranking[0]["ingresos"] > 0 else None,
    }
    if ant:
        reporte["periodo_anterior"] = ant.como_dict()
    return reporte


# ---------------- CSV ----------------
COLUMNAS_CSV = ["origen", "producto", "unidades", "ingresos", "participacion_pct", "unidades_anterior",
                "ingresos_anterior", "variacion_ingresos", "variacion_pct", "periodo_inicio", "periodo_fin",
                "periodo_anterior_inicio", "periodo_anterior_fin", "moneda"]


def _celda(valor, decimales: int | None = None):
    if valor is None:
        return ""
    if isinstance(valor, str):
        return "'" + valor if valor[:1] in ("=", "+", "-", "@", "\t", "\r") else valor  # inyección de fórmulas
    return f"{valor:.{decimales}f}" if decimales is not None else valor


def escribir_csv(reporte: dict, destino: TextIO) -> None:
    """Formato largo: una fila por origen y producto, más filas TOTAL. La columna 'origen' nunca se omite."""
    p, pa = reporte["periodo"], reporte.get("periodo_anterior") or {}
    cola = [p["inicio"], p["fin"], pa.get("inicio", ""), pa.get("fin", ""), reporte["moneda"]]
    escritor = csv.writer(destino, lineterminator="\n")
    escritor.writerow(COLUMNAS_CSV)

    def fila(origen, producto, d, total=False):
        escritor.writerow([
            origen, _celda(producto), d.get("unidades"), _celda(d.get("ingresos"), 2),
            "" if total else _celda(d.get("participacion_pct"), 1), _celda(d.get("unidades_anterior")),
            _celda(d.get("ingresos_anterior"), 2), _celda(d.get("variacion_ingresos"), 2),
            _celda(d.get("variacion_pct", d.get("variacion_ingresos_pct")), 1), *cola])

    for origen, seccion in reporte["origenes"].items():
        for producto in seccion["productos"]:
            fila(origen, producto["producto"], producto)
        fila(origen, "TOTAL", seccion["total"], total=True)
    if len(reporte["origenes"]) > 1:
        fila("combinado", "TOTAL", reporte["total_combinado"], total=True)


def guardar_csv(reporte: dict, nombre: str, carpeta: Path = CARPETA_REPORTES) -> Path:
    """Escribe en `carpeta/nombre`. Solo nombres simples '*.csv'; nunca sobrescribe un archivo existente."""
    if not _NOMBRE_CSV.match(nombre):
        raise ValueError("nombre de archivo inválido: use letras, números, '-' o '_' y extensión .csv")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    with open(ruta, "x", encoding="utf-8-sig", newline="") as archivo:  # BOM: Excel abre bien los acentos
        escribir_csv(reporte, archivo)
    return ruta
