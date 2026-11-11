/** Markdown mínimo y seguro para las respuestas del agente. Solo produce un árbol de datos (sin HTML):
 * el componente lo convierte en elementos de React, así que ningún texto del modelo se interpreta como HTML
 * (React escapa todo) y los enlaces no se vuelven activos. Soporta: párrafos, títulos, listas, tablas,
 * **negrita**, *cursiva* y `código`. */

export type Inline =
  | { t: "texto"; v: string }
  | { t: "negrita" | "cursiva" | "codigo"; v: Inline[] }
  | { t: "br" };

export type Alineacion = "izq" | "der" | "centro";

export type Bloque =
  | { t: "parrafo"; v: Inline[] }
  | { t: "titulo"; nivel: 3 | 4 | 5; v: Inline[] }
  | { t: "lista"; ordenada: boolean; items: Inline[][] }
  | { t: "tabla"; cabecera: Inline[][]; alin: Alineacion[]; filas: Inline[][][] };

const INLINE = /\*\*([^*]+?)\*\*|__([^_]+?)__|`([^`]+?)`|\*([^*\s][^*]*?)\*|(?<![\w])_([^_\s][^_]*?)_(?![\w])|\[([^\]]+)\]\((?:[^()]|\([^()]*\))*\)/g;

export function parsearInline(texto: string): Inline[] {
  const salida: Inline[] = [];
  let ultimo = 0;
  for (const m of texto.matchAll(INLINE)) {
    if (m.index > ultimo) salida.push({ t: "texto", v: texto.slice(ultimo, m.index) });
    if (m[1] ?? m[2]) salida.push({ t: "negrita", v: parsearInline((m[1] ?? m[2])!) });
    else if (m[3]) salida.push({ t: "codigo", v: [{ t: "texto", v: m[3] }] });
    else if (m[4] ?? m[5]) salida.push({ t: "cursiva", v: parsearInline((m[4] ?? m[5])!) });
    else salida.push({ t: "texto", v: m[6]! }); // enlace: solo el texto visible, nunca un <a>
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) salida.push({ t: "texto", v: texto.slice(ultimo) });
  return salida;
}

const celdas = (linea: string): string[] => {
  let s = linea.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
};
const esFilaTabla = (l: string) => l.includes("|") && l.trim().length > 1;
const esSeparador = (l: string) => /^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$/.test(l) && l.includes("-");
const RE_TITULO = /^(#{1,6})\s+(.*)$/;
const RE_UL = /^\s*[-*+]\s+(.*)$/;
const RE_OL = /^\s*\d+[.)]\s+(.*)$/;

export function parsearMarkdown(fuente: string): Bloque[] {
  const lineas = fuente.replace(/\r\n?/g, "\n").split("\n");
  const bloques: Bloque[] = [];
  let i = 0;
  while (i < lineas.length) {
    const linea = lineas[i]!;
    if (!linea.trim()) { i++; continue; }

    if (esFilaTabla(linea) && i + 1 < lineas.length && esSeparador(lineas[i + 1]!)) {
      const cab = celdas(linea);
      const alin = celdas(lineas[i + 1]!).map<Alineacion>((c) =>
        c.startsWith(":") && c.endsWith(":") ? "centro" : c.endsWith(":") ? "der" : "izq");
      i += 2;
      const filas: Inline[][][] = [];
      while (i < lineas.length && lineas[i]!.trim() && esFilaTabla(lineas[i]!)) {
        const fila = celdas(lineas[i]!);
        filas.push(cab.map((_, k) => parsearInline(fila[k] ?? "")));
        i++;
      }
      bloques.push({ t: "tabla", cabecera: cab.map(parsearInline), alin: cab.map((_, k) => alin[k] ?? "izq"), filas });
      continue;
    }

    const titulo = RE_TITULO.exec(linea);
    if (titulo) {
      // # y ## se reducen: dentro de una respuesta de chat nunca compiten con el título de la conversación
      const nivel = Math.min(5, Math.max(3, titulo[1]!.length + 2)) as 3 | 4 | 5;
      bloques.push({ t: "titulo", nivel, v: parsearInline(titulo[2]!.replace(/\s+#+\s*$/, "")) });
      i++;
      continue;
    }

    const re = RE_UL.test(linea) ? RE_UL : RE_OL.test(linea) ? RE_OL : null;
    if (re) {
      const items: Inline[][] = [];
      while (i < lineas.length && re.test(lineas[i]!)) {
        items.push(parsearInline(re.exec(lineas[i]!)![1]!));
        i++;
      }
      bloques.push({ t: "lista", ordenada: re === RE_OL, items });
      continue;
    }

    // párrafo: líneas consecutivas hasta un hueco o el inicio de otro bloque
    const partes: string[] = [];
    while (i < lineas.length && lineas[i]!.trim() && !RE_TITULO.test(lineas[i]!) && !RE_UL.test(lineas[i]!)
      && !RE_OL.test(lineas[i]!) && !(esFilaTabla(lineas[i]!) && i + 1 < lineas.length && esSeparador(lineas[i + 1]!))) {
      partes.push(lineas[i]!.trim());
      i++;
    }
    const v: Inline[] = [];
    partes.forEach((p, k) => {
      if (k > 0) v.push({ t: "br" });
      v.push(...parsearInline(p));
    });
    bloques.push({ t: "parrafo", v });
  }
  return bloques;
}
