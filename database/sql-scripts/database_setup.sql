-- Execution order for QAstra database setup

-- Create the qastra login role with password
CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';

-- Create the qastra database owned by the qastra role
CREATE DATABASE qastra OWNER qastra;

-- Grant full database privileges to the qastra role
GRANT ALL PRIVILEGES ON DATABASE qastra TO qastra;

-- Create a dedicated schema for qastra under the qastra role
CREATE SCHEMA qastraschema AUTHORIZATION qastra;

-- Grant all schema-level privileges to the qastra role
GRANT ALL ON SCHEMA qastraschema TO qastra;

-- Set the default search path so qastraschema is resolved first
ALTER ROLE qastra SET search_path TO qastraschema, public;

-- Verify that the qastraschema was created successfully
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'qastraschema';
