-- ============================================
-- QAstra Local Database Setup Script
-- Creates the database, application user, schema, and grants privileges.
--
-- IMPORTANT: This script must be run in TWO parts in DBeaver:
--
-- PART 1 (connected to 'postgres' database as superuser):
--   Run steps 1-3: Create role, create database, grant privileges
--   NOTE: CREATE DATABASE cannot run inside a transaction block.
--         In DBeaver, right-click the SQL editor -> set "Auto-commit" ON,
--         or run the CREATE DATABASE statement separately.
--
-- PART 2 (switch connection to 'qastra' database):
--   Run step 4: Create schema and grant privileges
-- ============================================

-- 1. Create application role (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qastra') THEN
        CREATE ROLE qastra WITH LOGIN PASSWORD 'qastra123';
    END IF;
END$$;

-- 2. Create application database (if not exists)
-- NOTE: CREATE DATABASE cannot run inside a transaction block.
-- In DBeaver, run this statement separately if needed.
SELECT 'CREATE DATABASE qastra OWNER qastra'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'qastra');
-- If the above SELECT returns a row, run manually:
--   CREATE DATABASE qastra OWNER qastra;

-- 3. Grant privileges on the database
GRANT ALL PRIVILEGES ON DATABASE qastra TO qastra;

-- ============================================
-- PART 1 ENDS HERE.
-- STOP: Now switch your DBeaver connection to the 'qastra' database
-- before running the section below.
-- ============================================

-- ============================================
-- PART 2: Run this connected to the 'qastra' database
-- ============================================

-- 4. Create schema and grant privileges
CREATE SCHEMA IF NOT EXISTS qastraschema AUTHORIZATION qastra;
GRANT ALL ON SCHEMA qastraschema TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON TABLES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON SEQUENCES TO qastra;
ALTER DEFAULT PRIVILEGES IN SCHEMA qastraschema GRANT ALL ON FUNCTIONS TO qastra;

-- Done!
-- Next: Run the migration scripts in backend/alembic/sql/migration/ (00 through 15)
SELECT 'Setup complete! Now run migration scripts in backend/alembic/sql/migration/' AS next_step;
