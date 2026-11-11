/** Cliente HTTP de la API. Rutas relativas ("/api/v1/..."): en desarrollo las resuelve el proxy de Vite
 * (ver vite.config.ts), que añade la cabecera Authorization del lado de Node. Este archivo nunca ve la clave. */
import type {
  ConversacionResumen, EjecucionDetalle, EjecucionResumen, MensajeApi, ParametrosReporte, ReporteVentas,
  RespuestaChat,
} from "./tipos";

/** Mismo formato único que agentflow/api/errors.py: {error:{codigo,mensaje,solicitud_id,campos?}}. */
export class ErrorAPI extends Error {
  status: number;
  codigo: string;
  solicitudId: string | null;
  campos: { campo: string; mensaje: string }[] | null;

  constructor(status: number, codigo: string, mensaje: string, solicitudId: string | null = null, campos: { campo: string; mensaje: string }[] | null = null) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.solicitudId = solicitudId;
    this.campos = campos;
  }
}

async function peticion<T>(ruta: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`/api${ruta}`, { ...init, headers: { ...init?.headers, Accept: "application/json" } });
  } catch {
    // sin red o backend caído: distinto de un error del servidor, para que la interfaz lo explique distinto
    throw new ErrorAPI(0, "sin_conexion", "No se pudo contactar con el servidor. Verifica que la API esté en marcha.");
  }
  if (r.status === 204) return undefined as T;
  const contentType = r.headers.get("content-type") || "";
  const cuerpo = contentType.includes("application/json") ? await r.json().catch(() => null) : null;
  if (!r.ok) {
    const error = cuerpo?.error;
    if (!error && [502, 503, 504].includes(r.status)) {
      // el proxy de desarrollo (o un proxy inverso) responde sin el formato de la API cuando FastAPI no está arriba
      throw new ErrorAPI(r.status, "sin_conexion", "No se pudo contactar con el servidor. Verifica que la API esté en marcha.");
    }
    throw new ErrorAPI(r.status, error?.codigo ?? "error_desconocido", error?.mensaje ?? "Ocurrió un error inesperado.",
      error?.solicitud_id ?? null, error?.campos ?? null);
  }
  return cuerpo as T;
}

const query = (params: Record<string, string | number | undefined>) => {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
};

export const crearConversacion = () => peticion<{ id: string }>("/v1/conversaciones", { method: "POST" });

export const listarConversaciones = (limite = 20) =>
  peticion<ConversacionResumen[]>(`/v1/conversaciones${query({ limite })}`);

export const obtenerMensajes = (conversacionId: string, limite = 50) =>
  peticion<MensajeApi[]>(`/v1/conversaciones/${conversacionId}/mensajes${query({ limite })}`);

export const listarEjecucionesDeConversacion = (conversacionId: string, limite = 20) =>
  peticion<EjecucionResumen[]>(`/v1/conversaciones/${conversacionId}/ejecuciones${query({ limite })}`);

export const detalleEjecucion = (ejecucionId: string) =>
  peticion<EjecucionDetalle>(`/v1/ejecuciones/${ejecucionId}`);

export const enviarMensaje = (conversacionId: string, contenido: string) =>
  peticion<RespuestaChat>(`/v1/conversaciones/${conversacionId}/mensajes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contenido }),
  });

export const reporteVentas = (p: ParametrosReporte) =>
  peticion<ReporteVentas>(`/v1/reportes/ventas${query(p)}`);

/** Descarga el CSV (generado en memoria por la API) como archivo, sin navegar fuera de la aplicación. */
export async function descargarReporteCsv(p: ParametrosReporte): Promise<void> {
  const r = await fetch(`/api/v1/reportes/ventas.csv${query(p)}`, { headers: { Accept: "text/csv" } });
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => null);
    const error = cuerpo?.error;
    throw new ErrorAPI(r.status, error?.codigo ?? "error_desconocido", error?.mensaje ?? "No se pudo generar el CSV.");
  }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "reporte_ventas.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
