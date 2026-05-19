-- ============================================
-- Migration: 0300da16b3d7 - Add original_steps to test_results
-- Date: 2026-03-31
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_results ADD COLUMN IF NOT EXISTS original_steps JSONB;

-- Stamp alembic version
UPDATE alembic_version SET version_num = '0300da16b3d7';

COMMIT;
