-- ============================================
-- QAstra Database Setup — Step 1 of 2
-- Run connected to the 'postgres' database as a superuser.
--
-- IMPORTANT: In DBeaver, enable Auto-commit (right-click editor → Auto-commit ON)
--            because CREATE DATABASE cannot run inside a transaction block.
--
-- Creates the application role and database.
-- Values must match your .env file (DB_USER, DB_PASSWORD, DB_NAME).
-- ============================================

-- 1. Create application role
-- (If role already exists, this will error — safe to ignore)
CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';

-- 2. Create application database
-- (If database already exists, this will error — safe to ignore)
CREATE DATABASE qastra OWNER qastra;

-- 3. Grant privileges on the database
GRANT ALL PRIVILEGES ON DATABASE qastra TO qastra;
