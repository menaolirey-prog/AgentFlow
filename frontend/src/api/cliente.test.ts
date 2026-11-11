/** Pruebas del cliente HTTP con `fetch` simulado: ninguna llamada real a la API ni a Groq/Gemini. */
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ErrorAPI, crearConversacion, descargarReporteCsv, enviarMensaje, listarConversaciones, reporteVentas,
} from "./cliente";

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "content-type": "application/json" } });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("peticion (envoltorio fetch)", () => {
  it("llama a la ruta relativa /api/... y devuelve el cuerpo en éxito", async () => {
    const fetchFalso = vi.fn().mockResolvedValue(json({ id: "c1" }, 201));
    vi.stubGlobal("fetch", fetchFalso);

    const r = await crearConversacion();

    expect(r).toEqual({ id: "c1" });
    expect(fetchFalso).toHaveBeenCalledWith("/api/v1/conversaciones", expect.objectContaining({ method: "POST" }));
  });

  it("traduce el formato único de error de la API a ErrorAPI", async () => {
    const cuerpo = { error: { codigo: "no_encontrado", mensaje: "Conversación no encontrada.", solicitud_id: "req-1" } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(cuerpo, 404)));

    await expect(listarConversaciones()).rejects.toMatchObject(
      { status: 404, codigo: "no_encontrado", message: "Conversación no encontrada.", solicitudId: "req-1" });
  });

  it("un fallo de red (backend caído) da un ErrorAPI propio, no una excepción cruda", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await listarConversaciones().catch((e) => e);

    expect(error).toBeInstanceOf(ErrorAPI);
    expect(error.codigo).toBe("sin_conexion");
  });

  it("un 502 del proxy sin cuerpo JSON (FastAPI apagado) se explica como falta de conexión", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad Gateway", { status: 502 })));

    await expect(listarConversaciones()).rejects.toMatchObject({ status: 502, codigo: "sin_conexion" });
  });

  it("envía el mensaje como JSON a la ruta de la conversación", async () => {
    const respuesta = {
      respuesta: "Vendiste S/ 100.", estado: "ok", motivo: null, origen: "modelo", herramientas: [],
      tokens_entrada: 10, tokens_salida: 5, duracion_ms: 50, ejecucion_id: "e1", historial_guardado: true,
    };
    const fetchFalso = vi.fn().mockResolvedValue(json(respuesta));
    vi.stubGlobal("fetch", fetchFalso);

    const r = await enviarMensaje("conv-1", "¿Cuánto vendí?");

    expect(r.ejecucion_id).toBe("e1");
    const [ruta, init] = fetchFalso.mock.calls[0];
    expect(ruta).toBe("/api/v1/conversaciones/conv-1/mensajes");
    expect(JSON.parse(init.body)).toEqual({ contenido: "¿Cuánto vendí?" });
  });
});

describe("reporteVentas", () => {
  it("arma la query string solo con los parámetros presentes", async () => {
    const fetchFalso = vi.fn().mockResolvedValue(json({ moneda: "PEN" }));
    vi.stubGlobal("fetch", fetchFalso);

    await reporteVentas({ periodo: "este_mes", origen: "real" });

    expect(fetchFalso.mock.calls[0][0]).toBe("/api/v1/reportes/ventas?periodo=este_mes&origen=real");
  });
});

describe("descargarReporteCsv", () => {
  it("lanza ErrorAPI si la API responde con error, sin intentar descargar nada", async () => {
    const cuerpo = { error: { codigo: "periodo_invalido", mensaje: "Periodo inválido." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(cuerpo, 422)));

    await expect(descargarReporteCsv({ periodo: "x", origen: "todos" }))
      .rejects.toMatchObject({ status: 422, codigo: "periodo_invalido" });
  });
});
