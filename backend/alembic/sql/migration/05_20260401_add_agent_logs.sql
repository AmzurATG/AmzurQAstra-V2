-- ============================================
-- Migration: a1b2c3d4e5f6 - Add agent_logs to test_results
-- Date: 2026-04-01
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_results ADD COLUMN IF NOT EXISTS agent_logs JSONB;

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'a1b2c3d4e5f6';
