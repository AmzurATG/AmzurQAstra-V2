-- ============================================
-- QAstra Local Database Setup Script
-- Creates the database, application user, schema, and grants privileges.
--
-- Run this in DBeaver connected to the 'postgres' database
-- as a PostgreSQL superuser (e.g. 'postgres').
--
-- After running this, connect to the 'qastra' database
-- and run the migration SQL scripts in backend/alembic/sql/migration/
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
-- STOP HERE. Now connect to the 'qastra' database
-- (change your DBeaver connection to 'qastra')
-- and run the section below.
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
