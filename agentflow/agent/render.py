"""Plantilla determinista de respaldo: presenta los datos sin intervención del modelo."""
from agentflow.tools.registry import ResultadoHerramienta


def _s(x: float) -> str:
    return f"S/ {x:,.2f}"


def _rango(d: dict) -> str:
    return f"{d['inicio']} al {d['fin']}"


def _pct(x) -> str:
    return "sin base de comparación" if x is None else f"{x:+.1f}%"


def _totales(d: dict) -> str:
    return (f"Ventas del {_rango(d['periodo'])}: {_s(d['ingresos_totales'])}, "
            f"{d['unidades']} unidades en {d['numero_ventas']} ventas.")


def _por_producto(d: dict) -> str:
    if not d["productos"]:
        return f"Sin ventas del {_rango(d['periodo'])}."
    lineas = [f"- {p['producto']}: {_s(p['ingresos'])} ({p['unidades']} unidades)" for p in d["productos"]]
    return f"Ventas por producto del {_rango(d['periodo'])}:\n" + "\n".join(lineas)


def _comparar(d: dict) -> str:
    a, b = d["actual"], d["anterior"]
    return (f"Periodo actual ({_rango(d['periodo_actual'])}): {_s(a['ingresos'])}, {a['unidades']} unidades.\n"
            f"Periodo anterior ({_rango(d['periodo_anterior'])}): {_s(b['ingresos'])}, {b['unidades']} unidades.\n"
            f"Variación de ingresos: {_s(d['variacion_ingresos'])} ({_pct(d['variacion_ingresos_pct'])}).")


def _caidas(d: dict) -> str:
    cabecera = f"{_rango(d['periodo_actual'])} frente a {_rango(d['periodo_anterior'])}"
    if not d["productos"]:
        return f"Ningún producto registró caída de ingresos ({cabecera})."
    lineas = [f"- {p['producto']}: {_s(p['ingresos_anterior'])} -> {_s(p['ingresos_actual'])} "
              f"({_pct(p['variacion_pct'])})" for p in d["productos"]]
    return f"Productos en caída ({cabecera}):\n" + "\n".join(lineas)


_FORMATOS = {"ventas_totales": _totales, "ventas_por_producto": _por_producto,
             "comparar_periodos": _comparar, "productos_en_caida": _caidas}


def plantilla_respaldo(resultados: list[ResultadoHerramienta]) -> str:
    bloques = [_FORMATOS[r.nombre](r.datos) for r in resultados if r.ok and r.nombre in _FORMATOS]
    return "\n\n".join(bloques) if bloques else "No pude obtener datos para responder a esta consulta."
