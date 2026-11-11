/** Metadatos reales (no son datos de muestra): descripciones de agentflow/tools/registry.py y texto de interfaz. */

export const DESCRIPCIONES: Record<string, string> = {
  ventas_totales: "Ingresos totales, unidades y número de ventas de un periodo.",
  ventas_por_producto: "Ventas agrupadas por producto, con ranking por ingresos o unidades.",
  comparar_periodos: "Compara ingresos y unidades entre dos periodos, con la variación ya calculada.",
  productos_en_caida: "Productos cuyos ingresos bajaron entre dos periodos, por mayor caída.",
  reporte_ventas: "Reporte comercial completo de un periodo, con real y demo por separado.",
};

export const SUGERENCIAS = [
  "¿Cuánto vendimos este mes frente al mes pasado?",
  "¿Qué productos cayeron más en octubre?",
  "Compara las últimas 4 semanas por producto.",
];

export const PRESETS_PERIODO = ["este_mes", "mes_anterior", "ultimos_7_dias", "ultimos_30_dias", "este_anio"] as const;
