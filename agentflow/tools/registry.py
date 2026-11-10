"""Registro de herramientas autorizadas: única puerta entre el modelo y el código/SQL."""
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from agentflow.observability.logging import registrar
from agentflow.tools import ventas
from agentflow.tools.schemas import (
    CompararPeriodosArgs, ProductosEnCaidaArgs, VentasPorProductoArgs, VentasTotalesArgs,
)

MENSAJE_ERROR_INTERNO = "No se pudo consultar los datos en este momento."


@dataclass(frozen=True)
class Herramienta:
    nombre: str
    descripcion: str
    modelo_args: type[BaseModel]
    funcion: Callable


@dataclass
class ResultadoHerramienta:
    nombre: str
    argumentos: dict | None
    ok: bool
    datos: dict
    duracion_ms: int
    codigo_error: str | None = None

    def contenido(self) -> str:
        return json.dumps(self.datos, ensure_ascii=False)


HERRAMIENTAS_VENTAS = (
    Herramienta("ventas_totales",
                "Ingresos totales, unidades y número de ventas de un periodo.",
                VentasTotalesArgs, ventas.ventas_totales),
    Herramienta("ventas_por_producto",
                "Ventas agrupadas por producto en un periodo, con ranking por ingresos o unidades.",
                VentasPorProductoArgs, ventas.ventas_por_producto),
    Herramienta("comparar_periodos",
                "Compara ingresos y unidades entre dos periodos (variación absoluta y porcentual ya calculada). "
                "Úsala para 'compara A con B'. Un periodo en curso se compara parcial contra uno completo.",
                CompararPeriodosArgs, ventas.comparar_periodos),
    Herramienta("productos_en_caida",
                "Productos cuyos ingresos bajaron entre dos periodos, ordenados por mayor caída.",
                ProductosEnCaidaArgs, ventas.productos_en_caida),
)


def _sin_titulos(nodo: Any) -> Any:
    """Quita 'title' del JSON Schema para ahorrar tokens."""
    if isinstance(nodo, dict):
        return {k: _sin_titulos(v) for k, v in nodo.items() if k != "title"}
    return nodo


class RegistroHerramientas:
    def __init__(self, repo, herramientas=HERRAMIENTAS_VENTAS):
        self._repo = repo
        self._herramientas = {h.nombre: h for h in herramientas}

    def esquemas(self) -> list[dict]:
        return [{"type": "function", "function": {
            "name": h.nombre, "description": h.descripcion,
            "parameters": _sin_titulos(h.modelo_args.model_json_schema())}}
            for h in self._herramientas.values()]

    def ejecutar(self, nombre: str, argumentos_json: str, hoy) -> ResultadoHerramienta:
        inicio = time.monotonic()

        def resultado(ok, datos, args=None, codigo=None):
            return ResultadoHerramienta(nombre, args, ok, datos, int((time.monotonic() - inicio) * 1000), codigo)

        herramienta = self._herramientas.get(nombre)
        if herramienta is None:
            return resultado(False, {"error": "herramienta_no_autorizada"}, codigo="herramienta_no_autorizada")
        try:
            bruto = json.loads(argumentos_json or "{}")
            if not isinstance(bruto, dict):
                raise ValueError("los argumentos deben ser un objeto JSON")
            args = herramienta.modelo_args.model_validate(bruto)
        except (ValidationError, ValueError) as error:
            detalle = ([f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors(include_url=False)]
                       if isinstance(error, ValidationError) else [str(error)])
            return resultado(False, {"error": "argumentos_invalidos", "detalle": detalle},
                             codigo="argumentos_invalidos")
        argumentos = args.model_dump()
        try:
            return resultado(True, herramienta.funcion(args, self._repo, hoy), argumentos)
        except ValueError as error:  # periodo imposible (inicio > fin, futuro...): mensaje propio y seguro
            return resultado(False, {"error": "argumentos_invalidos", "detalle": [str(error)]},
                             argumentos, "argumentos_invalidos")
        except Exception as error:  # DB caída, etc.: el detalle va solo al log, nunca al modelo ni al usuario
            registrar("error_herramienta", herramienta=nombre, tipo=type(error).__name__)
            return resultado(False, {"error": "error_interno", "mensaje": MENSAJE_ERROR_INTERNO},
                             argumentos, "error_interno")
