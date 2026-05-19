-- ============================================
-- Migration: m7n8o9p0q1r2 - Add live_progress to integrity_check_results
-- Date: 2026-05-01
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE integrity_check_results ADD COLUMN IF NOT EXISTS live_progress JSONB;

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'm7n8o9p0q1r2';

COMMIT;
