-- ============================================
-- QAstra Database Setup — Step 2 of 2
-- Run connected to the 'qastra' database as a superuser.
--
-- Creates the application schema and grants privileges.
-- Values must match your .env file (DB_SCHEMA).
-- ============================================

-- 1. Create schema owned by the application role
CREATE SCHEMA IF NOT EXISTS qastraschema AUTHORIZATION qastra;

-- 2. Grant schema-level privileges
GRANT ALL ON SCHEMA qastraschema TO qastra;

-- 3. Set default privileges so future objects are accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;

-- 4. Create alembic version tracking table
SET search_path TO qastraschema;
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

COMMIT;
