import { describe, expect, it } from "vitest";
import type { EjecucionResumen, MensajeApi } from "../api/tipos";
import { emparejarHistorial } from "./historial";

const mensaje = (rol: MensajeApi["rol"], contenido: string): MensajeApi => ({ rol, contenido });
const ejecucion = (id: string, iniciada_en: string): EjecucionResumen => ({
  id, estado: "ok", motivo: null, origen: "modelo", tokens: 100, duracion_ms: 500, iniciada_en, herramientas: 1,
});

describe("emparejarHistorial", () => {
  it("vincula cada turno con su ejecución cuando los conteos calzan, en orden cronológico", () => {
    const mensajes = [mensaje("user", "¿Cuánto vendí?"), mensaje("assistant", "S/ 100."), mensaje("user", "¿Y en demo?"), mensaje("assistant", "S/ 20.")];
    const ejecuciones = [ejecucion("e2", "2026-11-10T10:00:00Z"), ejecucion("e1", "2026-11-10T09:00:00Z")]; // desc, como la API

    const turnos = emparejarHistorial(mensajes, ejecuciones);

    expect(turnos).toHaveLength(2);
    expect(turnos[0]).toMatchObject({ pregunta: "¿Cuánto vendí?", respuesta: "S/ 100.", resumen: { id: "e1" } });
    expect(turnos[1]).toMatchObject({ pregunta: "¿Y en demo?", respuesta: "S/ 20.", resumen: { id: "e2" } });
  });

  it("si los conteos no calzan (hubo turnos con error, que no se guardan) no inventa una vinculación", () => {
    const mensajes = [mensaje("user", "hola"), mensaje("assistant", "¡Hola!")];
    const ejecuciones = [ejecucion("e1", "2026-11-10T09:00:00Z"), ejecucion("e2", "2026-11-10T09:05:00Z")];

    const turnos = emparejarHistorial(mensajes, ejecuciones);

    expect(turnos).toHaveLength(1);
    expect(turnos[0].resumen).toBeNull();
  });

  it("sin mensajes no produce turnos", () => {
    expect(emparejarHistorial([], [])).toEqual([]);
  });
});
