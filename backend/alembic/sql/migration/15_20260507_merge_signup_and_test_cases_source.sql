-- ============================================
-- Migration: m3r4g5e6s7g8n9 - Merge signup + test_cases.source branches
-- Date: 2026-05-07
-- This is a merge migration — no schema changes.
-- ============================================

SET search_path TO qastraschema;

-- Stamp alembic version to the final merged head
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('m3r4g5e6s7g8n9');

COMMIT;
