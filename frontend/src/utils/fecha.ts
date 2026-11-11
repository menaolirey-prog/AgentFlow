export type Grupo = "Hoy" | "Ayer" | "Anteriores";

const mismoDiaLocal = (a: Date, b: Date) => a.toDateString() === b.toDateString();

export function agruparFecha(iso: string): Grupo {
  const fecha = new Date(iso);
  const hoy = new Date();
  if (mismoDiaLocal(fecha, hoy)) return "Hoy";
  const ayer = new Date(hoy);
  ayer.setDate(ayer.getDate() - 1);
  if (mismoDiaLocal(fecha, ayer)) return "Ayer";
  return "Anteriores";
}

export function formatoCuando(iso: string, grupo: Grupo): string {
  const fecha = new Date(iso);
  if (grupo === "Hoy") return fecha.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
  return fecha.toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}
