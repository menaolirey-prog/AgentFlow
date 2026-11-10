"""Argumentos de las herramientas. Pydantic rechaza todo lo no declarado antes de llegar a SQL."""
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from agentflow.tools.periodos import PRESETS, validar_sintaxis


def _periodo_valido(valor: str) -> str:
    validar_sintaxis(valor)
    return valor.strip()


PeriodoTexto = Annotated[str, AfterValidator(_periodo_valido)]
_FORMATO = f"{', '.join(repr(p) for p in PRESETS)} o un rango 'AAAA-MM-DD/AAAA-MM-DD' (inclusivo)"


class _ArgsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _periodo_opcional(valor: str) -> str:
    return "" if not valor.strip() else _periodo_valido(valor)


class ReporteVentasArgs(_ArgsBase):
    periodo: PeriodoTexto = Field(description=f"Periodo del reporte: {_FORMATO}.")
    comparar_con: Annotated[str, AfterValidator(_periodo_opcional)] = Field(
        default="", description="Periodo base para comparar (mismo formato); vacío si no se pide comparación.")
    origen: Literal["todos", "real", "demo"] = Field(
        default="todos", description="'real' = solo ventas reales, 'demo' = solo ficticias, 'todos' = ambas por separado.")


class VentasTotalesArgs(_ArgsBase):
    periodo: PeriodoTexto = Field(description=f"Periodo a consultar: {_FORMATO}.")


class VentasPorProductoArgs(_ArgsBase):
    periodo: PeriodoTexto = Field(description=f"Periodo a consultar: {_FORMATO}.")
    ordenar_por: Literal["ingresos", "unidades"] = Field(default="ingresos", description="Criterio de orden.")
    limite: int = Field(default=10, ge=1, le=50, description="Máximo de productos a devolver.")


class CompararPeriodosArgs(_ArgsBase):
    periodo_actual: PeriodoTexto = Field(description=f"Periodo reciente: {_FORMATO}.")
    periodo_anterior: PeriodoTexto = Field(description=f"Periodo base de comparación: {_FORMATO}.")


class ProductosEnCaidaArgs(_ArgsBase):
    periodo_actual: PeriodoTexto = Field(description=f"Periodo reciente: {_FORMATO}.")
    periodo_anterior: PeriodoTexto = Field(description=f"Periodo base de comparación: {_FORMATO}.")
    limite: int = Field(default=5, ge=1, le=20, description="Máximo de productos a devolver.")
