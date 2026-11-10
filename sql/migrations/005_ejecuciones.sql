-- Idempotente. Registro de ejecuciones del agente (una por solicitud) y de las herramientas que usó.
-- Aplicar como administrador. Reversión: sql/migrations/down/005_ejecuciones.down.sql
-- Privacidad: NO se guarda el texto de la pregunta ni de la respuesta (están en 'mensajes'), solo su longitud;
-- tampoco mensajes de error: solo códigos. Los argumentos guardados son los ya validados (periodos, límites).
CREATE TABLE IF NOT EXISTS ejecuciones (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversacion_id uuid        REFERENCES conversaciones (id) ON DELETE SET NULL,  -- NULL: sesión sin persistir
    estado          text        NOT NULL DEFAULT 'en_curso'
                    CHECK (estado IN ('en_curso', 'ok', 'degradado', 'limite', 'error')),
    motivo          text        CHECK (char_length(motivo) <= 60),
    origen          text        CHECK (origen IN ('modelo', 'plantilla', 'mensaje_error')),
    pregunta_chars  integer     NOT NULL CHECK (pregunta_chars >= 0),
    tokens_entrada  integer     NOT NULL DEFAULT 0 CHECK (tokens_entrada >= 0),
    tokens_salida   integer     NOT NULL DEFAULT 0 CHECK (tokens_salida >= 0),
    llamadas_llm    integer     NOT NULL DEFAULT 0 CHECK (llamadas_llm >= 0),
    duracion_ms     integer     CHECK (duracion_ms >= 0),
    iniciada_en     timestamptz NOT NULL DEFAULT now(),
    finalizada_en   timestamptz
);
CREATE INDEX IF NOT EXISTS idx_ejecuciones_conversacion ON ejecuciones (conversacion_id, iniciada_en DESC);
CREATE INDEX IF NOT EXISTS idx_ejecuciones_iniciada ON ejecuciones (iniciada_en DESC);

CREATE TABLE IF NOT EXISTS ejecucion_herramientas (
    id           bigint   GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ejecucion_id uuid     NOT NULL REFERENCES ejecuciones (id) ON DELETE CASCADE,
    orden        smallint NOT NULL CHECK (orden >= 1),
    herramienta  text     NOT NULL CHECK (char_length(herramienta) <= 60),
    argumentos   jsonb,                       -- NULL si fueron rechazados antes de validarse
    ok           boolean  NOT NULL,
    codigo_error text     CHECK (char_length(codigo_error) <= 60),
    duracion_ms  integer  NOT NULL CHECK (duracion_ms >= 0),
    UNIQUE (ejecucion_id, orden)
);

-- Una ejecución finalizada es inmutable: solo se puede actualizar mientras está 'en_curso'.
CREATE OR REPLACE FUNCTION ejecuciones_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.estado <> 'en_curso' THEN
        RAISE EXCEPTION 'la ejecucion % ya esta finalizada', OLD.id;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_ejecuciones_inmutables ON ejecuciones;
CREATE TRIGGER trg_ejecuciones_inmutables BEFORE UPDATE ON ejecuciones
    FOR EACH ROW EXECUTE FUNCTION ejecuciones_inmutables();

-- Permisos mínimos: insertar, leer, y actualizar SOLO las columnas de cierre. Sin DELETE.
REVOKE ALL ON ejecuciones, ejecucion_herramientas FROM agentflow_app;
GRANT SELECT, INSERT ON ejecuciones, ejecucion_herramientas TO agentflow_app;
GRANT UPDATE (estado, motivo, origen, tokens_entrada, tokens_salida, llamadas_llm, duracion_ms, finalizada_en)
    ON ejecuciones TO agentflow_app;
