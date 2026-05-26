-- Execution order for QAstra database setup

-- Create the qastra login role with password (skip if already exists)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qastra') THEN
        CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';
    END IF;
END $$;

-- Create the qastra database owned by the qastra role (skip if already exists)
-- NOTE: CREATE DATABASE cannot run inside a DO block or transaction.
-- Run this line manually if it errors out:
CREATE DATABASE qastra OWNER qastra;

-- Grant full database privileges to the qastra role
GRANT ALL PRIVILEGES ON DATABASE qastra TO qastra;

-- Create a dedicated schema for qastra under the qastra role
CREATE SCHEMA IF NOT EXISTS qastraschema AUTHORIZATION qastra;

-- Grant all schema-level privileges to the qastra role
GRANT ALL ON SCHEMA qastraschema TO qastra;

-- Grant default privileges so future objects are accessible to qastra
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;

-- Set the default search path so qastraschema is resolved first
ALTER ROLE qastra SET search_path TO qastraschema, public;

-- Verify that the qastraschema was created successfully
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'qastraschema';
