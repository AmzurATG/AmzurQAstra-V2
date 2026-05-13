-- ============================================
-- Migration: n8o9p0q1r2s3 - Add test_cases.source column
-- Date: 2026-05-06
-- ============================================

SET search_path TO qastraschema;

ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS source VARCHAR(16) NOT NULL DEFAULT 'manual';

-- Backfill: AI-generated test cases get source='ai'
UPDATE test_cases SET source = 'ai' WHERE is_generated = true;

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'n8o9p0q1r2s3';
