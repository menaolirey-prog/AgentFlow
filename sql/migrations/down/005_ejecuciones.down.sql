-- Reversión de 005. DESTRUCTIVA: elimina el registro de ejecuciones. Aplicar como administrador.
DROP TABLE IF EXISTS ejecucion_herramientas;
DROP TABLE IF EXISTS ejecuciones;
DROP FUNCTION IF EXISTS ejecuciones_inmutables();
