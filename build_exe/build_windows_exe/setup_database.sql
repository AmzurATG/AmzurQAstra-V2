-- =====================================================
-- QAstra Database Setup (Run ONCE before first launch)
-- =====================================================
-- Works in DBeaver, pgAdmin, or any SQL client.
--
-- Values must match your .env file:
--   DB_USER     = qastra
--   DB_PASSWORD = qastra123
--   DB_NAME     = qastra
--   DB_SCHEMA   = qastraschema
-- =====================================================

-- =====================================================
-- STEP 1: Connect to the "postgres" database as superuser
--         and run the following:
-- =====================================================

-- 1a. Create the application role
CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';

-- 1b. Create the application database
CREATE DATABASE qastra OWNER qastra;

-- =====================================================
-- STEP 2: Now disconnect and reconnect to the "qastra"
--         database as superuser, then run the following:
-- =====================================================

-- 2a. Create the application schema
CREATE SCHEMA IF NOT EXISTS qastraschema AUTHORIZATION qastra;

-- 2b. Grant privileges
GRANT ALL ON SCHEMA qastraschema TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;

-- =====================================================
-- Done! Now place .env next to QAstra.exe and launch.
-- Alembic migrations + admin user creation happen
-- automatically on first startup.
-- =====================================================
