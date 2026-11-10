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
- Fase 2 completa: historial ✔ · ejecuciones ✔ · reportes ✔ (`/reporte`, tool `reporte_ventas`, CSV en `reportes/`, ignorado por git). Siguiente: Fase 3 FastAPI (requiere aprobación).
- Ejecuciones: `ejecuciones`/`ejecucion_herramientas`; guardan IDs, estado, tokens, duración y códigos de error, nunca texto. Una fila `en_curso` antigua = desenlace desconocido (proceso interrumpido).
- Pendiente a futuro: propiedad de conversaciones por usuario (hoy no hay autenticación), FastAPI (F3), React (F4).
- Reportes: datos `real` y `demo` siempre por separado (total combinado explícito). Migración 006 (pendiente de aplicar) marca las ventas 1-3 del prototipo como demo; tras aplicarla no habrá ventas reales y la sección real sale en cero. `cerrar_interrumpidas` (al iniciar la CLI) marca `en_curso` antiguas como error/interrumpida (desenlace desconocido).
