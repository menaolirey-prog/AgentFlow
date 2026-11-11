import { Fragment } from "react";
import { parsearMarkdown, type Alineacion, type Inline } from "../utils/markdown";

function enLinea(nodos: Inline[]) {
  return nodos.map((n, i) => {
    switch (n.t) {
      case "texto": return <Fragment key={i}>{n.v}</Fragment>;
      case "br": return <br key={i} />;
      case "negrita": return <strong key={i}>{enLinea(n.v)}</strong>;
      case "cursiva": return <em key={i}>{enLinea(n.v)}</em>;
      case "codigo": return <code key={i} className="md__codigo">{enLinea(n.v)}</code>;
    }
  });
}

const CLASE_ALIN: Record<Alineacion, string> = { izq: "", der: "num", centro: "md__centro" };

/** Respuesta del agente en Markdown, construida solo con elementos de React (nunca innerHTML). */
export function Markdown({ texto }: { texto: string }) {
  return (
    <div className="md">
      {parsearMarkdown(texto).map((b, i) => {
        switch (b.t) {
          case "parrafo": return <p key={i} className="texto">{enLinea(b.v)}</p>;
          case "titulo": {
            const Etiqueta = `h${b.nivel}` as "h3" | "h4" | "h5";
            return <Etiqueta key={i} className="md__titulo">{enLinea(b.v)}</Etiqueta>;
          }
          case "lista": {
            const Lista = b.ordenada ? "ol" : "ul";
            return <Lista key={i} className="md__lista">{b.items.map((it, k) => <li key={k}>{enLinea(it)}</li>)}</Lista>;
          }
          case "tabla":
            return (
              <div key={i} className="bloque-tabla md__tabla" role="region" tabIndex={0} aria-label="Tabla de la respuesta">
                <table className="tabla">
                  <thead><tr>{b.cabecera.map((c, k) => <th key={k} scope="col" className={CLASE_ALIN[b.alin[k]!]}>{enLinea(c)}</th>)}</tr></thead>
                  <tbody>
                    {b.filas.map((f, r) => (
                      <tr key={r}>{f.map((c, k) => <td key={k} className={CLASE_ALIN[b.alin[k]!]}>{enLinea(c)}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
        }
      })}
    </div>
  );
}
