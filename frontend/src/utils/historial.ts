import type { EjecucionResumen, MensajeApi } from "../api/tipos";
import type { Turno } from "../tipos";

/** Empareja mensajes (user/assistant alternados) con sus ejecuciones por orden cronológico.
 * Un turno con error no se guarda en `mensajes` (ver agent/orchestrator.py), así que si una conversación
 * tuvo turnos con error, los conteos no calzan: en ese caso se muestra el historial sin traza por turno
 * en vez de arriesgar vincular una ejecución con el mensaje equivocado. */
export function emparejarHistorial(mensajes: MensajeApi[], ejecuciones: EjecucionResumen[]): Turno[] {
  const usuarios = mensajes.filter((m) => m.rol === "user");
  const asistentes = mensajes.filter((m) => m.rol === "assistant");
  const ascendente = [...ejecuciones].sort((a, b) => a.iniciada_en.localeCompare(b.iniciada_en));
  const vinculable = asistentes.length === ascendente.length;

  return asistentes.map((a, i) => {
    const ejec = vinculable ? ascendente[i] : null;
    return {
      id: ejec?.id ?? `hist-${i}`,
      pregunta: usuarios[i]?.contenido ?? "",
      respuesta: a.contenido,
      resumen: ejec
        ? { id: ejec.id, estado: ejec.estado, motivo: ejec.motivo, origen: ejec.origen, tokens: ejec.tokens, duracionMs: ejec.duracion_ms, herramientasCount: ejec.herramientas }
        : null,
    };
  });
}
