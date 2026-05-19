-- ============================================
-- QAstra Full Teardown Script
-- Drops everything: schema, database, and role.
--
-- IMPORTANT: In DBeaver, enable Auto-commit (right-click editor → Auto-commit ON)
--            because DROP DATABASE cannot run inside a transaction block.
--
-- Run connected to the 'postgres' database as a superuser.
-- Do NOT run this while connected to the 'qastra' database.
-- ============================================

-- 1. Terminate active connections to the qastra database
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'qastra' AND pid <> pg_backend_pid();

-- 2. Drop the database
DROP DATABASE IF EXISTS qastra;

-- 3. Clean up all ownership and privileges, then drop the role
REASSIGN OWNED BY qastra TO postgres;
DROP OWNED BY qastra;
DROP ROLE IF EXISTS qastra;
