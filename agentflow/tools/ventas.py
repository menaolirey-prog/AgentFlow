"""Herramientas de ventas. El código calcula todas las cifras; el modelo solo las redacta."""
from datetime import date

from agentflow.config import MONEDA
from agentflow.tools.periodos import resolver_periodo
from agentflow.tools.reportes import construir_reporte
from agentflow.tools.schemas import (
    CompararPeriodosArgs, ProductosEnCaidaArgs, ReporteVentasArgs, VentasPorProductoArgs, VentasTotalesArgs,
)


def _dinero(valor) -> float:
    return round(float(valor), 2)


def _pct(cambio, base) -> float | None:
    return round(float(cambio) / float(base) * 100, 1) if base else None


def reporte_ventas(args: ReporteVentasArgs, repo, hoy: date) -> dict:
    return construir_reporte(repo, args.periodo, args.comparar_con or None, args.origen, hoy)


def ventas_totales(args: VentasTotalesArgs, repo, hoy: date) -> dict:
    p = resolver_periodo(args.periodo, hoy)
    r = repo.resumen(p.inicio, p.fin_exclusivo)
    return {"moneda": MONEDA, "periodo": p.como_dict(), "ingresos_totales": _dinero(r.ingresos),
            "unidades": r.unidades, "numero_ventas": r.n_ventas}


def ventas_por_producto(args: VentasPorProductoArgs, repo, hoy: date) -> dict:
    p = resolver_periodo(args.periodo, hoy)
    filas = repo.por_producto(p.inicio, p.fin_exclusivo, args.ordenar_por, args.limite)
    productos = [{"producto": n, "unidades": int(u), "ingresos": _dinero(i)} for n, u, i in filas]
    return {"moneda": MONEDA, "periodo": p.como_dict(), "ordenado_por": args.ordenar_por,
            "limite": args.limite, "productos": productos}


def comparar_periodos(args: CompararPeriodosArgs, repo, hoy: date) -> dict:
    act, ant = resolver_periodo(args.periodo_actual, hoy), resolver_periodo(args.periodo_anterior, hoy)
    ra, rb = repo.resumen(act.inicio, act.fin_exclusivo), repo.resumen(ant.inicio, ant.fin_exclusivo)
    return {
        "moneda": MONEDA,
        "periodo_actual": act.como_dict(), "periodo_anterior": ant.como_dict(),
        "actual": {"ingresos": _dinero(ra.ingresos), "unidades": ra.unidades, "numero_ventas": ra.n_ventas},
        "anterior": {"ingresos": _dinero(rb.ingresos), "unidades": rb.unidades, "numero_ventas": rb.n_ventas},
        "variacion_ingresos": _dinero(ra.ingresos - rb.ingresos),
        "variacion_ingresos_pct": _pct(ra.ingresos - rb.ingresos, rb.ingresos),
        "variacion_unidades": ra.unidades - rb.unidades,
        "variacion_unidades_pct": _pct(ra.unidades - rb.unidades, rb.unidades),
    }


def productos_en_caida(args: ProductosEnCaidaArgs, repo, hoy: date) -> dict:
    act, ant = resolver_periodo(args.periodo_actual, hoy), resolver_periodo(args.periodo_anterior, hoy)
    filas = repo.caidas((act.inicio, act.fin_exclusivo), (ant.inicio, ant.fin_exclusivo), args.limite)
    productos = [{"producto": n, "ingresos_actual": _dinero(a), "ingresos_anterior": _dinero(b),
                  "caida": _dinero(b - a), "variacion_pct": _pct(a - b, b)} for n, a, b in filas]
    return {"moneda": MONEDA, "periodo_actual": act.como_dict(), "periodo_anterior": ant.como_dict(),
            "productos": productos}
