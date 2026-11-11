# AgentFlow — frontend (Fase 4): diseño UX/UI

Estado: **entrega 2** (integración funcional con FastAPI). La entrega 1 (diseño) está aprobada y no cambia.
Contexto de producto: `PRODUCT.md`. Contrato de dirección visual: `.impeccable/surfaces/frontend-src-app-tsx.md`.

## Iniciar backend y frontend (dos terminales, desde la raíz del repo)
Requisitos: PostgreSQL local, `.env` con `AGENTFLOW_API_KEY` (≥ 32 caracteres), `GROQ_API_KEY` y `DB_*` (los valores solo en `.env`).
```
# Terminal 1: API (FastAPI)
.venv\Scripts\python.exe -m uvicorn agentflow.api.app:crear_app_desde_entorno --factory --host 127.0.0.1

# Terminal 2: interfaz (Vite)
cd frontend
npm install        # solo la primera vez
npm run dev        # http://127.0.0.1:5173
```
El navegador solo habla con `http://127.0.0.1:5173`; Vite reenvía `/api/*` a FastAPI (`127.0.0.1:8000`, o `AGENTFLOW_API_URL` si se define).
Si la API no está arriba, la interfaz lo dice («No se pudo contactar con el servidor») y ofrece reintentar.
`npm run build` genera `frontend/dist/`; `npm run typecheck` valida TypeScript; `npm test` corre las pruebas (`fetch` simulado, sin red).
Si Vite avisa «Outdated Optimize Dep» tras instalar paquetes: `npx vite --force`.

## Dirección visual: «Kardex»
Ficha de control de inventario de una tienda peruana, sin ornamento: papel neutro azulado, tinta grafito, filas separadas por
reglas finas, cifras tabulares alineadas a la derecha. Rechaza el chat de IA genérico (burbujas con brillo, tarjetas, morado):
la respuesta es texto sobrio y **su procedencia vive en un panel contextual compuesto como ficha** (orden · herramienta ·
argumentos · estado · ms). Una sola tinta de sello azul para selección, acción primaria y foco; verde/ámbar/rojo mate solo
como estado (OK, demo/aviso, error).

## Tokens (`frontend/src/styles/tokens.css`)
| Grupo | Valores |
|---|---|
| Tipografía | Geist Variable (interfaz) · Geist Mono Variable solo para identificadores, argumentos y cifras. Escala fija: 12 / 13 / 15 / 17 px; cuerpo 15 px, interlineado 1,55; medida 68ch |
| Espacio | base 4: 4 · 8 · 12 · 16 · 24 · 32 · 48; radio 6 px; riel 232 px; panel 360 px |
| Movimiento | solo estado, 150 ms, `cubic-bezier(.22,1,.36,1)`; sin animaciones de carga; respeta `prefers-reduced-motion` |
| Claro | fondo `oklch(.985 .004 250)` · riel `.958 .009 255` · panel `.972 .006 252` · tinta `.24 .02 260` · acento `.45 .14 258` |
| Oscuro | fondo `oklch(.19 .012 255)` · riel `.16 .014 255` · panel `.215 .013 255` · tinta `.94 .008 255` · acento `.76 .12 255` |
| Estado | ok / advertencia / error con variantes por tema (todos ≥ 4,5:1 sobre su fondo) |

Sin gradientes, brillos, sombras decorativas ni tarjetas: la jerarquía sale de reglas de 1 px, peso y tamaño.

## Estructura
- **Riel** (escritorio 232 px; en móvil, barra superior + navegación inferior): Agente · Conversaciones · Ejecuciones · Reportes, y
  **selector de tema visible** (Claro / Sistema / Oscuro, `radiogroup`) con la preferencia en `localStorage["agentflow.tema"]`.
  Un script en `index.html` aplica el tema antes del primer pintado (sin parpadeo).
- **Chat** (pantalla principal): cabecera, hilo (`role="log"`), línea de traza bajo cada respuesta, compositor con contador (límite 4000, igual que la API).
- **Panel de herramientas**: columna fija ≥ 1100 px; cajón sobre el contenido en pantallas menores; cerrado al inicio en móvil.
- Las demás pantallas muestran un marcador; se construyen en las siguientes entregas.
- Datos de muestra: `frontend/src/data/muestra.ts` (ficticios, rotulados «Datos de muestra» en pantalla; con la forma de `EjecucionDetalle`).
- Accesibilidad: salto al contenido, foco visible, `aria-current`, `aria-pressed`, tablas con `scope`, contraste AA, navegación por teclado.

## Seguridad de la clave (propuesta original)
Principio: `AGENTFLOW_API_KEY` **no existe en el navegador**. CORS no la protege: solo decide qué orígenes leen respuestas; cualquier
cliente no-navegador (curl) o un bundle que la contenga la expone igualmente. Todo valor en un bundle de React es público.

1. **Desarrollo local (entrega de integración):** el servidor de Vite hace de proxy `/api → http://127.0.0.1:8000` e **inyecta**
   `Authorization: Bearer <clave>` leyéndola de `.env` en Node (variable sin prefijo `VITE_`, por lo que Vite nunca la incrusta).
   El navegador llama a `/api/...` del mismo origen y no ve la clave. Verificación: `grep` del bundle `dist/` sin `Bearer`/`AGENTFLOW`
   (hoy ya se cumple) y prueba automática equivalente.
2. **Demo pública (futuro):** un BFF mínimo (o proxy inverso) delante de FastAPI que (a) guarda la clave solo en el servidor,
   (b) autentica a la persona con su propio login y cookie `HttpOnly; Secure; SameSite=Strict`, (c) expone solo lo necesario, en modo
   **solo lectura sobre datos demo** y con límites por sesión. FastAPI solo escucha en red privada. Sigue siendo una clave
   compartida, no multiusuario: la identidad por usuario (JWT/OAuth + propietario) es una fase posterior.
3. **Descartado:** formulario que pega la clave en el navegador (pasa por el cliente) y `VITE_*` con la clave.

## Rediseño de la pantalla principal (entrega 1b)
Tras la crítica con Impeccable: riel con navegación + **conversaciones recientes** (Hoy/Ayer/Anteriores) y «Nueva conversación»;
hilo en una columna de lectura de 760 px donde **la pregunta es el título de cada intercambio**; cuatro tipos de respuesta
(conversacional, cifra destacada solo en respuestas numéricas, tabla real/demo separadas con total combinado explícito, error con
recuperación) y estado vacío con sugerencias; **traza expandible** bajo cada respuesta; panel de detalle del paso solo en ≥ 1200 px
(en menos, el detalle se despliega en la fila); compositor de una línea que crece hasta 200 px; en móvil, barra compacta + cajón
de navegación. Los datos siguen siendo de muestra (`src/data/muestra.ts`).

## Integración con la API (entrega 2)
**Clave.** Implementado el proxy de desarrollo: `frontend/vite.config.ts` (código de Node, nunca empaquetado) lee `AGENTFLOW_API_KEY`
del `.env` de la raíz con `loadEnv` y la añade como `Authorization: Bearer` a cada petición `/api/*` que reenvía a FastAPI. El código
React solo usa rutas relativas (`/api/v1/...`). Verificado: `dist/` y `src/` no contienen `AGENTFLOW_API_KEY` ni `Bearer`. Sigue
siendo una clave compartida de un solo usuario; para una demo pública se necesita el BFF con login propio (no implementado).

**Pantallas conectadas** (`frontend/src/api/cliente.ts` es el único punto de acceso HTTP):
| Pantalla | Endpoints | Estados |
|---|---|---|
| Agente (chat) | `POST /v1/conversaciones` (se crea sola al enviar el primer mensaje), `POST .../mensajes`, `GET .../mensajes`, `GET .../ejecuciones`, `GET /v1/ejecuciones/{id}` | cargando historial, «el agente está pensando», vacío con sugerencias, errores 404/422/429/503/sin conexión, respuestas degradadas o con error en aviso |
| Conversaciones y riel | `GET /v1/conversaciones`, reanudar = cargar mensajes | cargando, vacío, error con reintento |
| Ejecuciones | `GET .../ejecuciones`, `GET /v1/ejecuciones/{id}` | por conversación (la API no tiene listado global) |
| Reportes | `GET /v1/reportes/ventas` y `.csv` | formulario, cargando, error, real y demo en tablas separadas con total combinado explícito |

**Decisiones por honestidad de datos.**
- La API devuelve la respuesta del agente como texto; no hay cifras ni tablas estructuradas en el chat. Por eso el chat muestra
  prosa y la traza real; las cifras y tablas del diseño se usan en Reportes, que sí devuelve datos estructurados real/demo.
- Se retiraron los datos de muestra y la sección «Origen de los datos» del panel: el endpoint de ejecuciones no dice qué filas
  (real o demo) tocó cada herramienta.
- `GET .../mensajes` no indica qué ejecución produjo cada mensaje. Se vinculan por orden solo si los conteos calzan; los turnos
  con error no se guardan en el historial, y en ese caso no se muestra traza por turno en vez de arriesgar una vinculación errónea.
- Dependencias nuevas (solo desarrollo): `@types/node` (tipado del proxy en `vite.config.ts`) y `vitest` (pruebas). `vitest.config.ts`
  usa `pool: "vmThreads"` porque el pool por defecto falla en este entorno.

## Cierre de la Fase 4 (entrega 3): validación y limitaciones

**Validación realizada** (sin llamadas a Groq/Gemini):
- Pruebas: `pytest` (unitarias), `pytest -m integration` (PostgreSQL local, solo lectura/historial) y `cd frontend; npm test` (vitest: cliente HTTP con `fetch` simulado, emparejado de historial, parser Markdown, estados de carga/error/vacío por render estático, seguridad del código fuente).
- Seguridad: ningún archivo de `frontend/src` referencia `AGENTFLOW_API_KEY`, `Bearer` ni `Authorization`; el bundle (`dist/`) tampoco. La clave solo se lee en `vite.config.ts` (Node).
- Markdown del chat (`src/utils/markdown.ts`, `components/Markdown.tsx`): el árbol se convierte en elementos de React; el HTML del modelo se muestra como texto, no hay `innerHTML`/`dangerouslySetInnerHTML` y los enlaces `[texto](url)` se reducen a su texto (sin `<a>` ni `javascript:`).
- Responsive: revisado a 390, 900 y 1440 px en claro y oscuro (chat con tabla, reportes, ejecuciones, estados vacío y error), sin desbordamiento horizontal de la página; las tablas anchas se desplazan dentro de su contenedor.

**Limitaciones conocidas**
- **Usuario único**: una clave compartida; no hay cuentas ni propiedad de conversaciones. Quien tiene la clave ve todo.
- **Proxy local**: la inyección de la clave ocurre solo en el servidor de desarrollo de Vite (`npm run dev`). `vite preview` o un despliegue estático no la inyectan. Una demo pública requiere un BFF con login propio y cookie HttpOnly (pendiente, no implementado).
- **Datos ficticios**: las 84 ventas son demo (`es_demo`, migración 006); no hay ventas reales. El agente y los reportes las rotulan como demostración; los reportes separan siempre real y demo.
- El chat devuelve texto: no hay cifras/tablas estructuradas en la respuesta, solo el Markdown del modelo y la traza real de herramientas.
- La API no vincula mensaje y ejecución; si hubo turnos con error, el historial reanudado no muestra traza por turno.
- Limitadores en memoria (un solo proceso) y sin pruebas del flujo con el modelo real en esta fase.
