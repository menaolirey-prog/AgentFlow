/** La clave de la API nunca puede llegar al código del navegador (Node-only en vite.config.ts). */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const archivos = (dir: string): string[] =>
  readdirSync(dir).flatMap((n) => {
    const ruta = join(dir, n);
    return statSync(ruta).isDirectory() ? archivos(ruta) : [ruta];
  });

const sinComentarios = (t: string) => t.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

describe("seguridad del frontend", () => {
  const fuente = archivos(join(import.meta.dirname)).filter((f) => /\.(tsx?|css|html)$/.test(f) && !f.endsWith("seguridad.test.ts") && !/\.test\.tsx?$/.test(f));

  it("ningún archivo de src referencia la clave ni usa cabeceras Authorization/Bearer", () => {
    for (const f of fuente) {
      const texto = readFileSync(f, "utf8");
      expect(sinComentarios(texto), f).not.toMatch(/AGENTFLOW_API_KEY|Bearer|Authorization|VITE_[A-Z_]*KEY/);
    }
  });

  it("ningún archivo de src usa innerHTML ni dangerouslySetInnerHTML", () => {
    for (const f of fuente) expect(sinComentarios(readFileSync(f, "utf8")), f).not.toMatch(/dangerouslySetInnerHTML|innerHTML/);
  });

  it("el proxy lee la clave solo en vite.config.ts y sin prefijo VITE_", () => {
    const cfg = readFileSync(join(import.meta.dirname, "..", "vite.config.ts"), "utf8");
    expect(cfg).toContain("AGENTFLOW_API_KEY");
    expect(cfg).not.toMatch(/VITE_|define\s*:/);
  });
});
