# AgentFlow

Agente comercial (retail peruano ficticio) con herramientas de ventas sobre PostgreSQL. Meta: plataforma de agentes
y automatizaciones. Documentación de producto futura en inglés; conversación y código en español.

## Comandos (Windows, desde la raíz)
- Pruebas unitarias (sin red): `.venv\Scripts\python.exe -m pytest`
- Integración (PostgreSQL local): `.venv\Scripts\python.exe -m pytest -m integration`
- Agente interactivo (consume cuota Groq): `.venv\Scripts\python.exe -m agentflow [--reanudar ID]`
- Migraciones: `sql/migrations/NNN_*.sql` (idempotentes) y `sql/migrations/down/` (reversión). **Las aplica el usuario
  como administrador con psql**; la app usa `agentflow_app` (permisos mínimos) y nunca DDL.

## Estructura
`agentflow/` → `agent/` (orchestrator, conversacion, verifier, render, prompts) · `tools/` (periodos, schemas, ventas,
registry) · `db/` (connection, repositories/{ventas,historial}) · `llm/` (base, groq_client) · `observability/` ·
`evals.py` · `cli.py`. Tests en `tests/{unit,integration,evals}`; `tests/fakes.py` tiene los dobles.
Archivos del prototipo en la raíz (`agente.py`, `herramientas.py`, `database.py`) se conservan; `test_herramientas.py` sigue activo.

## Decisiones que no deben romperse
- El modelo nunca escribe SQL ni fechas: elige herramienta y un periodo nominal; Pydantic valida; el código calcula.
- Todo SQL parametrizado; fragmentos variables solo desde mapas cerrados. Ingresos = `cantidad * ventas.precio_unitario`.
- Límites en `config.Limites` (iteraciones, herramientas, tiempo, tokens) los hace cumplir el orquestador.
- Cifras de la respuesta deben existir en los resultados de las herramientas (`verifier.py`); si no, plantilla determinista.
- Datos de prueba: `ventas.es_demo = true` (ficticios). Mantener la separación demo/real en reportes.
- Logs: JSON-lines sin claves ni texto de preguntas. Errores internos nunca llegan al usuario ni al modelo.
- Historial: tablas `conversaciones`/`mensajes`; la app solo tiene SELECT+INSERT. Un fallo al guardar no pierde la respuesta.

## Reglas de trabajo
- Ninguna llamada a Groq/Gemini ni servicios externos sin autorización explícita; pruebas con mocks.
- No leer ni mostrar `.env`. No hacer push. Una funcionalidad por entrega; esperar aprobación entre fases.
- Fases 1-2 completas (commits f2836d1). Fase 3 FastAPI: entrega 1 ✔ (base: app, auth, CORS, errores, middleware) · 2 ✔ (endpoints chat/conversaciones/ejecuciones/reportes, límites) · 3 ✔ (OpenAPI, CORS, no exposición de clave, docs). **Fase 3 completa.** Diseño en `docs/api-design.md`.
- Ejecuciones: `ejecuciones`/`ejecucion_herramientas`; guardan IDs, estado, tokens, duración y códigos de error, nunca texto. Una fila `en_curso` antigua = desenlace desconocido (proceso interrumpido).
- Pendiente a futuro: propiedad de conversaciones por usuario (hoy no hay autenticación), React (F4).
- Reportes: datos `real` y `demo` siempre por separado (total combinado explícito). Migración 006 (pendiente de aplicar) marca las ventas 1-3 del prototipo como demo; tras aplicarla no habrá ventas reales y la sección real sale en cero. `cerrar_interrumpidas` (al iniciar la CLI) marca `en_curso` antiguas como error/interrumpida (desenlace desconocido).

## API (Fase 3)
- Ejecutar: `.venv\Scripts\python.exe -m uvicorn agentflow.api.app:crear_app_desde_entorno --factory --host 127.0.0.1`
- `agentflow/api/`: `app` (fábrica `crear_app(ajustes, servicios)`), `config` (env: `AGENTFLOW_API_KEY` ≥32 car., `AGENTFLOW_CORS_ORIGINS`, `AGENTFLOW_ENV` dev|prod), `seguridad` (Bearer, fallo cerrado), `errors` (formato único), `middleware`, `servicios` (DI; Groq perezoso), `limites` (429: chat 10/min, 2 simultáneos, lecturas 120/min, 10 fallos auth/min), `esquemas` (Pydantic), `rutas/` (conversaciones, ejecuciones, reportes).
- Desarrollo: `AGENTFLOW_ENV=dev` habilita `/docs`; CORS local: `AGENTFLOW_CORS_ORIGINS=http://localhost:5173`. Detalle en `docs/api-design.md`.
- **Clave compartida, un solo usuario**: sin propietario de conversaciones; quien tiene la clave ve todo.
- Reglas: routers finos que reutilizan `Agente`/repos; protegidos con `requerir_api_key`; errores solo vía `ErrorAPI`; pruebas con `Servicios` falsos (nunca Groq); CORS sin `*`; el usuario genera la API key en su `.env`.

## Frontend (Fase 4)
- `frontend/` (Vite + React + TS, CSS propio con tokens en `src/styles/tokens.css`). Abrir: `cd frontend; npm install; npm run dev` → http://127.0.0.1:5173. Entrega 1 ✔ (diseño aprobado, tema claro/oscuro) · Entrega 2 ✔ (integración: `src/api/cliente.ts`, chat real, conversaciones, ejecuciones, reportes+CSV; sin datos de muestra). Pruebas: `npm test` (vitest, fetch simulado). **Fase 4 completa** (entrega 3: validación, Markdown seguro, responsive 390/900/1440, límites documentados en `docs/frontend-design.md`).
- `AGENTFLOW_API_KEY` nunca en el bundle (sin prefijo `VITE_`). Proxy de Vite (`vite.config.ts`, solo Node) lee la clave del `.env` raíz e inyecta Bearer en `/api/*`; demo pública = BFF con login propio (pendiente). Arranque: API con uvicorn (ver arriba) + `cd frontend; npm run dev`. Diseño: `docs/frontend-design.md`, `PRODUCT.md`.
- Limitaciones (Fase 4): usuario único con clave compartida; proxy de Vite solo en desarrollo local (demo pública = BFF pendiente); datos 100 % ficticios (`es_demo`). Las herramientas de ventas devuelven `origen_datos` (demo/real/mixto/sin_ventas); el agente nunca debe llamar reales a datos demo.
