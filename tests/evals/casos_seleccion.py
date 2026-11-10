"""Preguntas típicas del gerente comercial y la herramienta/argumentos que se espera. Fecha de referencia: 2026-11-10."""
from agentflow.evals import Caso

_MES = {"periodo_actual": "este_mes", "periodo_anterior": "mes_anterior"}

CASOS = [
    Caso("¿Cuánto vendimos este mes?", "ventas_totales", {"periodo": "este_mes"}),
    Caso("¿Cuánto vendimos el mes pasado?", "ventas_totales", {"periodo": "mes_anterior"}),
    Caso("Ventas totales de los últimos 7 días", "ventas_totales", {"periodo": "ultimos_7_dias"}),
    Caso("¿Cuánto vendimos en lo que va del año?", "ventas_totales", {"periodo": "este_anio"}),
    Caso("¿Cuántas unidades vendimos en septiembre?", "ventas_totales", {"periodo": "2026-09-01/2026-09-30"}),
    Caso("¿Qué productos generan mayores ingresos este mes?", "ventas_por_producto",
         {"periodo": "este_mes", "ordenar_por": "ingresos", "limite": 10}),
    Caso("Dame el top 3 de productos más vendidos en unidades los últimos 30 días", "ventas_por_producto",
         {"periodo": "ultimos_30_dias", "ordenar_por": "unidades", "limite": 3}),
    Caso("Ventas por producto del año", "ventas_por_producto",
         {"periodo": "este_anio", "ordenar_por": "ingresos", "limite": 10}),
    Caso("Compara las ventas de este mes con las del mes anterior", "comparar_periodos", _MES),
    Caso("¿Vendimos más en octubre que en septiembre?", "comparar_periodos",
         {"periodo_actual": "2026-10-01/2026-10-31", "periodo_anterior": "2026-09-01/2026-09-30"}),
    Caso("¿Qué productos registraron una caída este mes frente al anterior?", "productos_en_caida",
         {**_MES, "limite": 5}),
    Caso("¿Qué producto cayó más en octubre respecto a septiembre?", "productos_en_caida",
         {"periodo_actual": "2026-10-01/2026-10-31", "periodo_anterior": "2026-09-01/2026-09-30", "limite": 5}),
    Caso("Prepara un reporte de ventas de este mes", "reporte_ventas",
         {"periodo": "este_mes", "comparar_con": "", "origen": "todos"}),
    Caso("Genera un reporte de octubre comparado con septiembre", "reporte_ventas",
         {"periodo": "2026-10-01/2026-10-31", "comparar_con": "2026-09-01/2026-09-30", "origen": "todos"}),
]
