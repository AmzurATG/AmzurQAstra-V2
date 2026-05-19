-- ============================================
-- Migration: f8e9a1b2c3d4 - Widen requirements.file_type for long MIME types
-- Date: 2026-04-09
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE requirements ALTER COLUMN file_type TYPE VARCHAR(255);

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'f8e9a1b2c3d4';

COMMIT;
