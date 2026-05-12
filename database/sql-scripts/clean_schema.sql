-- ============================================
-- QAstra Schema Cleanup Script
-- Drops ALL objects in the 'qastraschema' schema.
-- Run in DBeaver against the 'qastra' database.
-- ============================================

-- 1. Drop all triggers
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT trigger_name, event_object_table
        FROM information_schema.triggers
        WHERE trigger_schema = 'qastraschema'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON qastraschema.%I CASCADE', r.trigger_name, r.event_object_table);
    END LOOP;
END $$;

-- 2. Drop all views
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'qastraschema'
    LOOP
        EXECUTE format('DROP VIEW IF EXISTS qastraschema.%I CASCADE', r.table_name);
    END LOOP;
END $$;

-- 3. Drop all tables
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'qastraschema'
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS qastraschema.%I CASCADE', r.tablename);
    END LOOP;
END $$;

-- 4. Drop all sequences
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'qastraschema'
    LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS qastraschema.%I CASCADE', r.sequence_name);
    END LOOP;
END $$;

-- 5. Drop all functions and procedures
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT p.oid, p.proname,
               CASE p.prokind WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END AS kind,
               pg_get_function_identity_arguments(p.oid) AS args
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'qastraschema'
    LOOP
        EXECUTE format('DROP %s IF EXISTS qastraschema.%I(%s) CASCADE', r.kind, r.proname, r.args);
    END LOOP;
END $$;

-- 6. Drop all custom types (enums, composites)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT t.typname
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'qastraschema'
          AND t.typtype IN ('e', 'c')
          AND left(t.typname, 1) != '_'
    LOOP
        EXECUTE format('DROP TYPE IF EXISTS qastraschema.%I CASCADE', r.typname);
    END LOOP;
END $$;

-- Done
SELECT 'All objects in qastraschema dropped successfully.' AS result;
