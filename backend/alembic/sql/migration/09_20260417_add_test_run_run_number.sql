-- ============================================
-- Migration: j3k4l5m6n7o8 - Add test_runs.run_number per-project sequence
-- Date: 2026-04-17
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_runs ADD COLUMN IF NOT EXISTS run_number INTEGER;

-- Backfill existing rows with sequential numbers per project
UPDATE test_runs AS t
SET run_number = s.rn
FROM (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS rn
    FROM test_runs
) AS s
WHERE t.id = s.id;

ALTER TABLE test_runs ALTER COLUMN run_number SET NOT NULL;

-- Add unique constraint (idempotent — drop first if exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_test_runs_project_run_number'
    ) THEN
        ALTER TABLE test_runs ADD CONSTRAINT uq_test_runs_project_run_number
            UNIQUE (project_id, run_number);
    END IF;
END$$;

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'j3k4l5m6n7o8';
