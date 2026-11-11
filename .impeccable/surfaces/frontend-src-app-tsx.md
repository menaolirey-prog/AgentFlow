---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: []
---

## Surface

Operate. Pantalla de chat del agente comercial (frontend React, `frontend/`). Usuario: gerente comercial, escritorio diario, móvil ocasional. Tarea: preguntar por ventas y comprobar cómo se obtuvo cada cifra. Esta entrega: estructura + pantalla de chat con datos de muestra rotulados; sin API ni Groq.

## Direction contract

THESIS: La confianza en una cifra es parte de la respuesta. Se rechaza el chat de IA genérico (burbujas, brillos, tarjetas): la respuesta es texto sobrio y su procedencia vive en un panel contextual compuesto como ficha de kardex.

OWN-WORLD: Kardex de tienda peruana, sin ornamento. Tinta grafito sobre papel neutro azulado (claro) / carbón de tinta (oscuro); riel lateral una capa más tintada; una sola tinta de sello azul para selección, acción primaria y foco; verde/ámbar/rojo mate solo para estado. Geist (UI) y Geist Mono solo para identificadores, argumentos y cifras tabulares. Filas separadas por reglas finas de 1px, columnas alineadas a la derecha con numerales tabulares; sin sombras decorativas.

STORY: El gerente pregunta, lee la respuesta con cifras y, con un clic en la línea de traza, ve qué herramientas se ejecutaron, con qué argumentos, cuánto tardaron y si fallaron. Entiende que real y demo van separados y que los datos mostrados son de muestra.

FIRST VIEWPORT: Escritorio 1440x900: riel de 232px (marca, Agente/Conversaciones/Ejecuciones/Reportes, selector Claro/Sistema/Oscuro abajo); centro con cabecera de conversación y rótulo "Datos de muestra", hilo con una respuesta que incluye tabla real/demo y línea de traza, compositor fijo abajo; panel derecho de 360px con la ejecución seleccionada. Acción primaria: Enviar, abajo a la derecha del compositor.

FORM: Kardex (candidato 7 de la lista propia; seed:1f632112e3eb5192). Aporta tipo, paleta, densidad y un gesto; la navegación y los controles son los estándar.

SIGNATURE: El panel de herramientas como ficha de kardex: columnas Orden · Herramienta · Argumentos · Estado · ms, con reglas continuas y sello de estado (OK / ERROR) en tinta; la línea de traza del hilo y la ficha comparten el mismo resalte de selección.

## Decisiones abiertas

Mecanismo de acceso a la API (proxy Vite en dev; BFF con login propio para demo): documentado en docs/frontend-design.md, no implementado.
