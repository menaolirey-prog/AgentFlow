"""SQL de ventas. Todo valor variable viaja como parámetro; nada se interpola desde el modelo."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from agentflow.db.connection import obtener_conexion_lectura

# Único fragmento SQL elegido por clave: valores constantes de un mapa cerrado.
_ORDEN = {"ingresos": "ingresos DESC", "unidades": "unidades DESC"}
_INGRESO = "v.cantidad * v.precio_unitario"  # precio vigente al momento de cada venta


@dataclass(frozen=True)
class ResumenVentas:
    ingresos: Decimal
    unidades: int
    n_ventas: int


class RepositorioVentas:
    def __init__(self, fabrica_conexion: Callable = obtener_conexion_lectura):
        self._fabrica = fabrica_conexion

    def _consultar(self, sql: str, params) -> list:
        with self._fabrica() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def resumen(self, inicio: date, fin_exclusivo: date) -> ResumenVentas:
        sql = f"""
            SELECT COALESCE(SUM({_INGRESO}), 0), COALESCE(SUM(v.cantidad), 0), COUNT(*)
            FROM ventas v
            WHERE v.fecha >= %s AND v.fecha < %s
        """
        ingresos, unidades, n = self._consultar(sql, (inicio, fin_exclusivo))[0]
        return ResumenVentas(Decimal(ingresos), int(unidades), int(n))

    def origenes(self, inicio: date, fin_exclusivo: date) -> tuple[bool, bool]:
        """(hay_demo, hay_real) en el rango: permite rotular el origen de las cifras de cualquier herramienta."""
        sql = """
            SELECT COALESCE(BOOL_OR(v.es_demo), false), COALESCE(BOOL_OR(NOT v.es_demo), false)
            FROM ventas v WHERE v.fecha >= %s AND v.fecha < %s
        """
        hay_demo, hay_real = self._consultar(sql, (inicio, fin_exclusivo))[0]
        return bool(hay_demo), bool(hay_real)

    def por_producto(self, inicio: date, fin_exclusivo: date, ordenar_por: str, limite: int) -> list[tuple]:
        orden = _ORDEN[ordenar_por]  # KeyError si no es una clave conocida
        sql = f"""
            SELECT p.nombre, SUM(v.cantidad) AS unidades, SUM({_INGRESO}) AS ingresos
            FROM ventas v JOIN productos p ON p.id_producto = v.id_producto
            WHERE v.fecha >= %s AND v.fecha < %s
            GROUP BY p.id_producto, p.nombre
            ORDER BY {orden}, p.nombre
            LIMIT %s
        """
        return self._consultar(sql, (inicio, fin_exclusivo, limite))

    def por_origen_producto(self, inicio: date, fin_exclusivo: date) -> list[tuple]:
        """(es_demo, producto, unidades, ingresos, n_ventas): base de los reportes, sin mezclar demo con real."""
        sql = f"""
            SELECT v.es_demo, p.nombre, SUM(v.cantidad), SUM({_INGRESO}), COUNT(*)
            FROM ventas v JOIN productos p ON p.id_producto = v.id_producto
            WHERE v.fecha >= %s AND v.fecha < %s
            GROUP BY v.es_demo, p.id_producto, p.nombre
            ORDER BY v.es_demo, p.nombre
        """
        return self._consultar(sql, (inicio, fin_exclusivo))

    def caidas(self, actual: tuple[date, date], anterior: tuple[date, date], limite: int) -> list[tuple]:
        """actual/anterior = (inicio, fin_exclusivo). Devuelve (nombre, ingresos_actual, ingresos_anterior)."""
        sql = f"""
            WITH agg AS (
                SELECT p.nombre,
                       SUM({_INGRESO}) FILTER (WHERE v.fecha >= %(a_ini)s AND v.fecha < %(a_fin)s) AS actual,
                       SUM({_INGRESO}) FILTER (WHERE v.fecha >= %(b_ini)s AND v.fecha < %(b_fin)s) AS anterior
                FROM ventas v JOIN productos p ON p.id_producto = v.id_producto
                WHERE (v.fecha >= %(a_ini)s AND v.fecha < %(a_fin)s)
                   OR (v.fecha >= %(b_ini)s AND v.fecha < %(b_fin)s)
                GROUP BY p.id_producto, p.nombre
            )
            SELECT nombre, COALESCE(actual, 0), COALESCE(anterior, 0)
            FROM agg
            WHERE COALESCE(actual, 0) < COALESCE(anterior, 0)
            ORDER BY COALESCE(anterior, 0) - COALESCE(actual, 0) DESC, nombre
            LIMIT %(limite)s
        """
        params = {"a_ini": actual[0], "a_fin": actual[1], "b_ini": anterior[0], "b_fin": anterior[1], "limite": limite}
        return self._consultar(sql, params)
