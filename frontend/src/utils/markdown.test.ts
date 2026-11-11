import { describe, expect, it } from "vitest";
import { parsearInline, parsearMarkdown } from "./markdown";

const TABLA = "| Producto | Unidades | Ingresos |\n|---|---:|---:|\n| Laptop | 5 | S/ 5,000.00 |\n| Mouse | 24 | S/ 850.50 |";

describe("parsearMarkdown", () => {
  it("convierte una tabla con alineación numérica", () => {
    const [t] = parsearMarkdown(TABLA);
    expect(t).toMatchObject({ t: "tabla", alin: ["izq", "der", "der"] });
    if (t?.t !== "tabla") throw new Error("no es tabla");
    expect(t.filas).toHaveLength(2);
    expect(t.filas[0]![2]).toEqual([{ t: "texto", v: "S/ 5,000.00" }]);
  });

  it("negrita, cursiva y código", () => {
    expect(parsearInline("**S/ 6,850.50** y *nota* con `x`")).toEqual([
      { t: "negrita", v: [{ t: "texto", v: "S/ 6,850.50" }] }, { t: "texto", v: " y " },
      { t: "cursiva", v: [{ t: "texto", v: "nota" }] }, { t: "texto", v: " con " },
      { t: "codigo", v: [{ t: "texto", v: "x" }] }]);
  });

  it("listas ordenadas y con viñetas", () => {
    expect(parsearMarkdown("1. **Laptop**\n2. Mouse")[0]).toMatchObject({ t: "lista", ordenada: true });
    expect(parsearMarkdown("- a\n- b")[0]).toMatchObject({ t: "lista", ordenada: false, items: [[{ t: "texto", v: "a" }], [{ t: "texto", v: "b" }]] });
  });

  it("títulos se reducen a h3 como mínimo y párrafos conservan saltos", () => {
    expect(parsearMarkdown("# Resumen")[0]).toMatchObject({ t: "titulo", nivel: 3 });
    const [p] = parsearMarkdown("línea 1\nlínea 2");
    expect(p).toMatchObject({ t: "parrafo" });
    expect(p?.t === "parrafo" && p.v.some((n) => n.t === "br")).toBe(true);
  });

  it("el HTML crudo queda como texto literal, nunca como elemento", () => {
    const [p] = parsearMarkdown('<img src=x onerror="alert(1)"> <script>alert(1)</script>');
    expect(p).toEqual({ t: "parrafo", v: [{ t: "texto", v: '<img src=x onerror="alert(1)"> <script>alert(1)</script>' }] });
  });

  it("los enlaces pierden la URL: solo se muestra el texto", () => {
    expect(parsearInline("[ver](javascript:alert(1))")).toEqual([{ t: "texto", v: "ver" }]);
  });

  it("un texto con barras pero sin separador no es tabla", () => {
    expect(parsearMarkdown("a | b")[0]).toMatchObject({ t: "parrafo" });
  });
});
