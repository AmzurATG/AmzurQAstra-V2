-- ============================================
-- Migration: l6n7o8p9q0r1 - Add pdf_path to test_recommendation_runs
-- Date: 2026-04-28
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_recommendation_runs ADD COLUMN IF NOT EXISTS pdf_path VARCHAR(500);

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'l6n7o8p9q0r1';
