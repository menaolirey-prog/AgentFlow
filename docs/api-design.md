# AgentFlow API — diseño (Fase 3)

Estado: **Fase 3 completa** (base, endpoints de negocio, cierre y validación). Siguiente: Fase 4 (React).

> **Modelo de acceso: clave compartida, un solo usuario.** Esta versión usa una única `AGENTFLOW_API_KEY`. No hay cuentas ni
> propietario de conversaciones: quien tenga la clave ve y puede continuar **todas** las conversaciones, ejecuciones y reportes.
> Los límites de uso son globales (no por usuario). No es apta para varios usuarios sin añadir identidad (JWT/OAuth + `propietario`).

## Principios
- La API es una capa fina: reutiliza `Agente`, `RegistroHerramientas` y los repositorios; no duplica lógica.
- Sin estado en el proceso: la conversación se rehidrata desde PostgreSQL en cada solicitud (`Conversacion.reanudar`).
- Endpoints síncronos (`def`): el código existente es síncrono; FastAPI los ejecuta en un pool de hilos.
- Español en rutas y campos, coherente con el dominio y el código.

## Endpoints
| Método y ruta | Auth | Entrega | Descripción |
|---|---|---|---|
| `GET /health` | no | 1 ✔ | Liveness (no toca la base). |
| `GET /v1/sesion` | sí | 1 ✔ | Valida la clave de API. |
| `POST /v1/conversaciones` | sí | 2 ✔ | Crea conversación → `201 {id}`. |
| `GET /v1/conversaciones` | sí | 2 ✔ | Lista (más recientes primero, `limite` 1–50). |
| `GET /v1/conversaciones/{id}/mensajes` | sí | 2 ✔ | Historial cronológico (`limite` 1–100, por defecto 50). |
| `POST /v1/conversaciones/{id}/mensajes` | sí | 2 ✔ | **Chat**: `{contenido}` (1–4000) → respuesta, estado, origen, herramientas usadas, tokens, `ejecucion_id`. |
| `GET /v1/conversaciones/{id}/ejecuciones` | sí | 2 ✔ | Ejecuciones de la sesión. |
| `GET /v1/ejecuciones/{id}` | sí | 2 ✔ | Detalle con herramientas (requiere `RegistroEjecuciones.detalle`). |
| `GET /v1/reportes/ventas` | sí | 2 ✔ | `periodo`, `comparar_con?`, `origen=todos|real|demo` → JSON del reporte. |
| `GET /v1/reportes/ventas.csv` | sí | 2 ✔ | Mismos parámetros → `text/csv` generado en memoria (no escribe en disco). |

## Decisiones
| Tema | Decisión | Por qué / límite |
|---|---|---|
| Autenticación | API key compartida, `Authorization: Bearer`, comparación en tiempo constante, mínimo 32 caracteres, **fallo cerrado** (sin clave configurada → 503). | Hay un solo usuario y las conversaciones no tienen propietario. **Límite:** quien tenga la clave ve todas las conversaciones. Con más usuarios: JWT/OAuth + columna `propietario` (nueva migración). |
| CORS | Lista explícita en `AGENTFLOW_CORS_ORIGINS`; vacía = sin CORS; `*` se rechaza al arrancar; solo `GET`/`POST`; sin credenciales (el token va en cabecera, no en cookie). | Mínimo privilegio para el futuro frontend (p. ej. `http://localhost:5173`). |
| Errores | Formato único `{"error": {codigo, mensaje, solicitud_id, campos?}}`; 401/404/405/413/422/429/500/503. Los 422 no repiten el valor enviado; los 500 no dan detalles. | Evita fugas y simplifica el cliente React. |
| Trazabilidad | `X-Request-ID` generado por el servidor; log JSON `http` (método, ruta, estado, duración) sin query, cabeceras ni cuerpo. | Las ejecuciones del agente ya tienen su propio ID. |
| Límites | Cuerpo ≤ 64 KB (por `Content-Length`); mensaje ≤ 4000 caracteres; **chat: 10 mensajes/min** (`AGENTFLOW_CHAT_POR_MINUTO`, 1–1000) y **máx. 2 chats simultáneos** (cada mensaje consume Groq); **lecturas, creaciones y reportes: 120/min**; **10 claves inválidas/min** (luego 429). Todo → `429` + `Retry-After`. Ventana deslizante en memoria, global (un proceso, un usuario). | El límite de cuerpo sin `Content-Length` (chunked) no se cubre aquí; lo mitiga el proxy delante. |
| Caché | `Cache-Control: no-store` y `nosniff` en todas las respuestas. | Los datos de conversaciones son privados. |
| Docs OpenAPI | Solo con `AGENTFLOW_ENV=dev`. | En producción no se publica el contrato. |
| Servicios | `Servicios` (historial, ejecuciones, ventas, `crear_agente`) inyectado en `crear_app`; el cliente de Groq se crea perezosamente. | Las pruebas usan dobles y nunca construyen Groq. |

## Detalles de la entrega 2
- El chat valida `{contenido}` con Pydantic (`extra=forbid`, recorta espacios, 1–4000 caracteres) y aplica límites antes de tocar la base o el modelo.
- IDs que no son UUID o no existen → `404` genérico (el ID no se refleja). Periodos de reporte inválidos → `422 periodo_invalido`.
- Reportes: `real` y `demo` siempre por separado; el CSV se genera en memoria (`reporte_ventas.csv`, con BOM para Excel).
- Aislamiento de datos: los routers solo usan los repositorios existentes (rol `agentflow_app`: SELECT/INSERT, sin DDL ni DELETE); el único método nuevo es `RegistroEjecuciones.detalle` (solo lectura, sin migración).
- Las respuestas de ejecuciones contienen solo metadatos (nunca texto de preguntas/respuestas).

## Variables de entorno (valores solo en `.env`, nunca en el repositorio)
`AGENTFLOW_API_KEY` (≥ 32 caracteres; generar con `python -c "import secrets; print(secrets.token_urlsafe(32))"`),
`AGENTFLOW_CORS_ORIGINS` (lista separada por comas), `AGENTFLOW_ENV` (`dev`|`prod`, por defecto `prod`), `AGENTFLOW_CHAT_POR_MINUTO` (opcional, por defecto 10),
más las existentes `DB_*` y `GROQ_API_KEY`.

## Desarrollo local (FastAPI + futuro React)
1. En `.env` (nunca en el repositorio): `AGENTFLOW_API_KEY=<≥32 caracteres>`, `AGENTFLOW_ENV=dev`,
   `AGENTFLOW_CORS_ORIGINS=http://localhost:5173` (origen de Vite; un solo origen explícito, sin `*`).
2. Iniciar: comando de la sección «Ejecutar» (escucha solo en `127.0.0.1:8000`).
3. Documentación interactiva: <http://127.0.0.1:8000/docs> (esquema en `/openapi.json`). **Solo con `AGENTFLOW_ENV=dev`**;
   en `prod` ambas rutas responden 404. En «Authorize» se pega la clave; el navegador la guarda solo en esa página.
4. CORS: solo `GET`/`POST`, cabeceras `Authorization` y `Content-Type`, sin credenciales ni cookies; `X-Request-ID` expuesto.
   Cualquier otro origen no recibe cabeceras CORS.

### Seguridad de la clave frente al navegador
- La clave es **compartida y de un solo usuario**; vive en `.env` del servidor y el usuario la introduce en el cliente.
  No debe incrustarse en el código de React ni en variables `VITE_*` (se publicarían en el bundle). Fase 4: pedirla en un
  formulario y guardarla solo en memoria (`sessionStorage` como mucho).
- La API nunca la devuelve: ni en respuestas, errores, OpenAPI ni logs (cubierto por pruebas); `Ajustes.__repr__` la oculta.
- Los límites de uso son **en memoria** (se reinician con el proceso, no se comparten entre procesos).

## Ejecutar
`.venv\Scripts\python.exe -m uvicorn agentflow.api.app:crear_app_desde_entorno --factory --host 127.0.0.1`

## Riesgos conocidos
- Límites en memoria: se reinician con el proceso y no se comparten entre procesos; con varios workers, usar el proxy o Redis.
- El límite de fallos de autenticación es global: un atacante que agote los 10 intentos/min también bloquea momentáneamente al usuario legítimo.
- Sin TLS propio: exponer solo detrás de un proxy HTTPS.
- Un único `Agente` por solicitud: la concurrencia la limita el pool de hilos y la cuota de Groq.
