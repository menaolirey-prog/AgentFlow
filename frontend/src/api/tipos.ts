/** Formas exactas de agentflow/api/esquemas.py y agentflow/tools/reportes.py. Ningún campo se inventa aquí. */

export type Estado = "ok" | "degradado" | "limite" | "error";
export type Origen = "modelo" | "plantilla" | "mensaje_error";

export type ConversacionResumen = { id: string; creada_en: string; mensajes: number; inicio: string | null };
export type MensajeApi = { rol: "user" | "assistant"; contenido: string };

export type HerramientaUsada = { nombre: string; ok: boolean; codigo_error: string | null; duracion_ms: number };
export type RespuestaChat = {
  respuesta: string;
  estado: Estado;
  motivo: string | null;
  origen: Origen;
  herramientas: HerramientaUsada[];
  tokens_entrada: number;
  tokens_salida: number;
  duracion_ms: number;
  ejecucion_id: string | null;
  historial_guardado: boolean;
};

export type EjecucionResumen = {
  id: string;
  estado: Estado;
  motivo: string | null;
  origen: Origen | null;
  tokens: number;
  duracion_ms: number | null;
  iniciada_en: string;
  herramientas: number;
};

export type HerramientaEjecutada = {
  orden: number;
  herramienta: string;
  argumentos: Record<string, unknown> | null;
  ok: boolean;
  codigo_error: string | null;
  duracion_ms: number;
};

export type EjecucionDetalle = {
  id: string;
  conversacion_id: string | null;
  estado: Estado;
  motivo: string | null;
  origen: Origen | null;
  pregunta_chars: number;
  tokens_entrada: number;
  tokens_salida: number;
  llamadas_llm: number;
  duracion_ms: number | null;
  iniciada_en: string;
  finalizada_en: string | null;
  herramientas: HerramientaEjecutada[];
};

/** agentflow/tools/reportes.py: construir_reporte / _totales / _productos. */
export type TotalPeriodo = {
  ingresos: number;
  unidades: number;
  numero_ventas: number;
  ingresos_anterior?: number;
  unidades_anterior?: number;
  variacion_ingresos?: number;
  variacion_ingresos_pct?: number | null;
  variacion_unidades?: number;
  variacion_unidades_pct?: number | null;
};
export type ProductoFila = {
  producto: string;
  unidades: number;
  ingresos: number;
  participacion_pct: number | null;
  unidades_anterior?: number;
  ingresos_anterior?: number;
  variacion_ingresos?: number;
  variacion_pct?: number | null;
};
export type SeccionOrigen = { total: TotalPeriodo; productos: ProductoFila[] };
export type ReporteVentas = {
  moneda: string;
  periodo: { inicio: string; fin: string };
  periodo_anterior?: { inicio: string; fin: string };
  origen_filtro: "todos" | "real" | "demo";
  contiene_datos_demo: boolean;
  advertencia: string | null;
  origenes: Partial<Record<"real" | "demo", SeccionOrigen>>;
  total_combinado: TotalPeriodo;
  producto_lider: string | null;
};

export type ParametrosReporte = { periodo: string; comparar_con?: string; origen: "todos" | "real" | "demo" };
