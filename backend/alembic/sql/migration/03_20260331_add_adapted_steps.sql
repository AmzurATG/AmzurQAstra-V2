-- ============================================
-- Migration: 2bd17a756caa - Add adapted_steps to test_results
-- Date: 2026-03-31
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_results ADD COLUMN IF NOT EXISTS adapted_steps JSONB;

-- Stamp alembic version
UPDATE alembic_version SET version_num = '2bd17a756caa';
