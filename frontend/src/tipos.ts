/** Tipos de vista (no son formas de la API): construidos a partir de RespuestaChat o de EjecucionResumen. */
import type { Estado, Origen } from "./api/tipos";

export type ResumenEjecucion = {
  id: string | null;
  estado: Estado;
  motivo: string | null;
  origen: Origen | null;
  tokens: number;
  duracionMs: number | null;
  herramientasCount: number;
};

export type Turno = { id: string; pregunta: string; respuesta: string; resumen: ResumenEjecucion | null };
