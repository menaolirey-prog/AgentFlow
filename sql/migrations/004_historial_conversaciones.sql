-- Idempotente. Historial de conversaciones, separado por sesión (conversacion_id).
-- Aplicar como administrador. Reversión: sql/migrations/down/004_historial_conversaciones.down.sql
CREATE TABLE IF NOT EXISTS conversaciones (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    creada_en  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mensajes (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversacion_id uuid        NOT NULL REFERENCES conversaciones (id) ON DELETE CASCADE,
    rol             text        NOT NULL CHECK (rol IN ('user', 'assistant')),
    contenido       text        NOT NULL CHECK (char_length(contenido) BETWEEN 1 AND 20000),
    creado_en       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON mensajes (conversacion_id, id);

-- Permisos mínimos: la aplicación solo lee e inserta (nunca modifica ni borra el historial).
REVOKE ALL ON conversaciones, mensajes FROM agentflow_app;
GRANT SELECT, INSERT ON conversaciones, mensajes TO agentflow_app;
-- Las columnas IDENTITY usan una secuencia interna: INSERT en la tabla basta, no requiere GRANT sobre la secuencia.
