-- ============================================
-- Migration: h1b2c3d4e5f6 - Add test_cases.case_number per-project sequence
-- Date: 2026-04-17
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS case_number INTEGER;

-- Backfill existing rows with sequential numbers per project
UPDATE test_cases AS t
SET case_number = s.rn
FROM (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS rn
    FROM test_cases
) AS s
WHERE t.id = s.id;

ALTER TABLE test_cases ALTER COLUMN case_number SET NOT NULL;

-- Add unique constraint
ALTER TABLE test_cases DROP CONSTRAINT IF EXISTS uq_test_cases_project_case_number;
ALTER TABLE test_cases ADD CONSTRAINT uq_test_cases_project_case_number
    UNIQUE (project_id, case_number);

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'h1b2c3d4e5f6';

COMMIT;
