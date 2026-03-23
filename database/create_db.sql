-- Run this FIRST to create the database and user
-- Execute as postgres superuser (connect to 'postgres' database)

-- Create user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'qastra') THEN
        CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';
    END IF;
END$$;

-- Create database
SELECT 'Creating database...' AS status;
-- Note: You may need to run this manually if connected to the database already:
-- CREATE DATABASE qastra OWNER qastra;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE qastra TO qastra;

SELECT 'Database and user created!' AS status;
SELECT 'Now connect to "qastra" database and run setup.sql' AS next_step;
