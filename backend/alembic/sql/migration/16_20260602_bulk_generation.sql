-- ============================================
-- Migration: p1q2r3s4t5u6 - Bulk generation: generation_jobs table,
--   test_cases.scenario_type + ac_ref columns, userstorysource enum extension
-- Date: 2026-06-02
-- ============================================

SET search_path TO qastraschema;

-- 1. Extend userstorysource enum with brd_generated value
ALTER TYPE userstorysource ADD VALUE IF NOT EXISTS 'brd_generated';

-- 2. Add scenario_type column to test_cases
ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS scenario_type VARCHAR(16) DEFAULT 'positive';

-- 3. Add ac_ref column to test_cases (links to acceptance criteria condition id)
ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS ac_ref VARCHAR(20) DEFAULT NULL;

-- 4. Create generation_jobs table for async bulk test generation tracking
CREATE TABLE IF NOT EXISTS generation_jobs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    profile VARCHAR(20) NOT NULL DEFAULT 'standard',
    story_ids JSONB NOT NULL DEFAULT '[]',
    total_stories INTEGER NOT NULL DEFAULT 0,
    completed_stories INTEGER NOT NULL DEFAULT 0,
    current_story_title VARCHAR(500) DEFAULT NULL,
    coverage_report_json JSONB DEFAULT NULL,
    error_message TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS ix_generation_jobs_project_id
    ON generation_jobs(project_id);
CREATE INDEX IF NOT EXISTS ix_generation_jobs_status
    ON generation_jobs(status);
CREATE INDEX IF NOT EXISTS ix_generation_jobs_created_by
    ON generation_jobs(created_by);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_generation_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generation_jobs_updated_at ON generation_jobs;
CREATE TRIGGER trg_generation_jobs_updated_at
    BEFORE UPDATE ON generation_jobs
    FOR EACH ROW EXECUTE FUNCTION update_generation_jobs_updated_at();

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'p1q2r3s4t5u6';

COMMIT;
