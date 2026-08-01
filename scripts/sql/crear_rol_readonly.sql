-- Rol de solo lectura para el MCP de Postgres (consultas desde Claude sin riesgo de escritura).
-- Ejecutar como superusuario:
--   psql -U postgres -h localhost -d all_in_django -f scripts/sql/crear_rol_readonly.sql
--
-- La clave se sustituye por la real; este archivo NO debe llevar la clave versionada.
-- Uso:  psql ... -v clave="'LA_CLAVE'"  (o edita el CREATE ROLE antes de correrlo).

CREATE ROLE all_in_django_ro WITH LOGIN PASSWORD :clave;

-- Solo lectura: sin permiso de crear objetos, sin escritura.
GRANT CONNECT ON DATABASE all_in_django TO all_in_django_ro;
GRANT USAGE ON SCHEMA public TO all_in_django_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO all_in_django_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO all_in_django_ro;

-- Que las tablas futuras (nuevas migraciones) también queden legibles.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO all_in_django_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE all_in_django IN SCHEMA public
    GRANT SELECT ON TABLES TO all_in_django_ro;
