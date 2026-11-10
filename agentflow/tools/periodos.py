"""Resolución determinista de periodos: el modelo nombra el periodo, el código calcula las fechas."""
import re
from dataclasses import dataclass
from datetime import date, timedelta

PRESETS = ("este_mes", "mes_anterior", "ultimos_7_dias", "ultimos_30_dias", "este_anio")
MAX_DIAS = 731
_RANGO = re.compile(r"^(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})$")


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fin: date  # inclusivo

    @property
    def fin_exclusivo(self) -> date:
        return self.fin + timedelta(days=1)

    def como_dict(self) -> dict:
        return {"inicio": self.inicio.isoformat(), "fin": self.fin.isoformat()}


def validar_sintaxis(texto: str) -> None:
    """Valida la forma del texto sin necesitar la fecha de hoy."""
    t = texto.strip()
    if t in PRESETS:
        return
    m = _RANGO.match(t)
    if not m:
        raise ValueError(f"periodo inválido; use {', '.join(PRESETS)} o 'AAAA-MM-DD/AAAA-MM-DD'")
    try:
        date.fromisoformat(m.group(1)), date.fromisoformat(m.group(2))
    except ValueError:
        raise ValueError("el rango contiene una fecha inexistente") from None


def resolver_periodo(texto: str, hoy: date) -> Periodo:
    validar_sintaxis(texto)
    t = texto.strip()
    if t == "este_mes":
        return Periodo(hoy.replace(day=1), hoy)
    if t == "mes_anterior":
        fin = hoy.replace(day=1) - timedelta(days=1)
        return Periodo(fin.replace(day=1), fin)
    if t == "ultimos_7_dias":
        return Periodo(hoy - timedelta(days=6), hoy)
    if t == "ultimos_30_dias":
        return Periodo(hoy - timedelta(days=29), hoy)
    if t == "este_anio":
        return Periodo(hoy.replace(month=1, day=1), hoy)

    inicio, fin = (date.fromisoformat(x) for x in t.split("/"))
    if inicio > fin:
        raise ValueError("la fecha de inicio es posterior a la de fin")
    if inicio > hoy:
        raise ValueError("el periodo empieza en el futuro")
    fin = min(fin, hoy)  # no hay ventas futuras; el periodo devuelto muestra el fin real usado
    if (fin - inicio).days + 1 > MAX_DIAS:
        raise ValueError(f"el periodo supera el máximo de {MAX_DIAS} días")
    return Periodo(inicio, fin)
