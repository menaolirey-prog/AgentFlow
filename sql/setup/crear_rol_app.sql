-- Crea el rol de la aplicación (permisos mínimos) si no existe. Ejecutar como administrador ANTES de 003:
--   psql -d <base> -v contrasena="'<elige-una-contraseña>'" -f sql/setup/crear_rol_app.sql
-- La contraseña se pasa por variable de psql: no se guarda en el repositorio. Úsala luego en DB_PASSWORD (.env).
-- Los permisos sobre tablas los otorgan las migraciones 003, 004 y 005 (SELECT/INSERT; nunca DDL).
SELECT format('CREATE ROLE agentflow_app LOGIN PASSWORD %L', :contrasena)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agentflow_app')
\gexec
