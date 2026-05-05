-- =====================================================
-- QAstra Database Setup (Run ONCE before first launch)
-- =====================================================
-- Execute this in pgAdmin or psql as the PostgreSQL superuser (postgres).
--
-- Values must match your .env file:
--   DB_USER     = qastra
--   DB_PASSWORD = qastra123
--   DB_NAME     = qastra
--   DB_SCHEMA   = qastraschema
-- =====================================================

-- 1. Create the application role
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qastra') THEN
        CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';
    END IF;
END$$;

-- 2. Create the application database
-- NOTE: CREATE DATABASE cannot run inside a transaction block.
-- In pgAdmin, run this statement separately if needed.
SELECT 'CREATE DATABASE qastra OWNER qastra'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qastra');
\gexec

-- 3. Connect to the new database and create the schema
\c qastra

CREATE SCHEMA IF NOT EXISTS qastraschema AUTHORIZATION qastra;
GRANT ALL ON SCHEMA qastraschema TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;

-- =====================================================
-- Done! Now configure .env and launch QAstra.exe.
-- Alembic migrations + admin user creation happen
-- automatically on first startup.
-- =====================================================
