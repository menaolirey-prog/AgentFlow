# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
React + TypeScript con Vite en `frontend/` (confirmado por el usuario). CSS propio con variables; sin librería de UI ni Tailwind. Backend FastAPI existente en `agentflow/api/` (no se modifica desde el frontend).

## Users
Gerente comercial de un retail peruano (ficticio), usuario único hoy. Consulta ventas, conversa con el agente, revisa qué herramientas ejecutó y saca reportes. Uso diario en escritorio, ocasional en móvil. Español.

## Product Purpose
AgentFlow es una plataforma de agentes y automatizaciones; el primer agente es comercial y responde preguntas de ventas usando herramientas sobre PostgreSQL. Éxito: respuestas con cifras verificables y trazabilidad de cómo se obtuvieron.

## Positioning
Cada cifra de una respuesta existe en el resultado de una herramienta (verificador) y cada ejecución deja traza auditable (herramientas, tokens, duración, códigos de error; nunca texto). Datos reales y demo siempre separados.

## Operating Context
Conversaciones persistentes, ejecuciones por solicitud, reportes por periodo con comparación y origen real/demo/todos, CSV. La API usa una sola clave compartida (un usuario) y límites en memoria.

## Capabilities and Constraints
Endpoints: `/v1/conversaciones` (crear, listar, mensajes, ejecuciones), `/v1/ejecuciones/{id}`, `/v1/reportes/ventas(.csv)`. Chat ≤4000 caracteres, 10 mensajes/min. Moneda y periodos definidos por el backend. Sin multiusuario todavía. Decisión abierta: mecanismo de demo pública (propuesto: BFF con login propio y datos demo).
La clave `AGENTFLOW_API_KEY` nunca debe llegar al bundle de React.

## Brand Commitments
Referencias declaradas por el usuario: Dify (chat y herramientas), LangSmith (trazas), Retool (reportes), Linear y Raycast (minimalismo, tipografía, navegación, jerarquía). Claro y oscuro con selector visible y preferencia persistente. Sin gradientes morados, brillos, tarjetas decorativas ni animaciones innecesarias. Chat como pantalla principal; menú lateral: Agente, Conversaciones, Ejecuciones, Reportes; panel contextual para herramientas ejecutadas.

## Evidence on Hand
Datos de ventas ficticios (`es_demo`). No hay clientes, logotipo ni testimonios reales; no inventar.

## Product Principles
1. La trazabilidad es parte de la respuesta, no un extra: cada cifra se puede rastrear a su herramienta.
2. Real y demo nunca se mezclan sin decirlo.
3. La herramienta desaparece en la tarea: familiaridad antes que originalidad en los controles.
4. Los errores nombran el problema y la recuperación, sin detalles internos.

## Accessibility & Inclusion
Accesible por teclado, contraste AA, foco visible, `prefers-reduced-motion`, responsive.
