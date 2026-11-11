/** Estados de carga, error y vacío, y render seguro de Markdown. Render estático: sin DOM ni red. */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ListaConversaciones } from "./ListaConversaciones";
import { Markdown } from "./Markdown";

const base = { conversaciones: [], cargando: false, error: null, onReintentar: () => {}, onAbrir: () => {}, onNueva: () => {} };

describe("ListaConversaciones: estados", () => {
  it("cargando", () => expect(renderToStaticMarkup(<ListaConversaciones {...base} cargando />)).toContain("Cargando conversaciones"));
  it("error con reintento", () => {
    const html = renderToStaticMarkup(<ListaConversaciones {...base} error="No se pudo contactar con el servidor." />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Reintentar");
  });
  it("vacío", () => expect(renderToStaticMarkup(<ListaConversaciones {...base} />)).toContain("Aún no hay conversaciones"));
  it("con datos", () => {
    const c = [{ id: "c1", creada_en: "2026-11-10T10:00:00Z", mensajes: 4, inicio: "¿Cuánto vendí?" }];
    const html = renderToStaticMarkup(<ListaConversaciones {...base} conversaciones={c as never} />);
    expect(html).toContain("¿Cuánto vendí?");
    expect(html).toContain("4 mensajes");
  });
});

describe("Markdown: render seguro", () => {
  it("tabla y negrita como elementos reales", () => {
    const html = renderToStaticMarkup(<Markdown texto={"| A | B |\n|---|---:|\n| **x** | 1 |"} />);
    expect(html).toContain("<table");
    expect(html).toContain("<strong>x</strong>");
    expect(html).toContain('<th scope="col" class="num">B</th>');
  });
  it("HTML del modelo se escapa: no hay etiquetas ejecutables", () => {
    const html = renderToStaticMarkup(<Markdown texto={'<script>alert(1)</script> <img src=x onerror=alert(1)>'} />);
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;");
  });
  it("los enlaces no generan <a> ni conservan javascript:", () => {
    const html = renderToStaticMarkup(<Markdown texto="[clic](javascript:alert(1)) y [web](https://x.com)" />);
    expect(html).not.toContain("<a");
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("href");
  });
});
