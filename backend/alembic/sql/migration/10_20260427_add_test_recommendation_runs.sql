-- ============================================
-- Migration: k5m6n7o8p9q0 - Add test_recommendation_runs table
-- Date: 2026-04-27
-- ============================================

SET search_path TO qastraschema;

CREATE TABLE IF NOT EXISTS test_recommendation_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result_json JSONB,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_test_recommendation_runs_project_id ON test_recommendation_runs(project_id);
CREATE INDEX IF NOT EXISTS ix_test_recommendation_runs_requirement_id ON test_recommendation_runs(requirement_id);
CREATE INDEX IF NOT EXISTS ix_test_recommendation_runs_created_by ON test_recommendation_runs(created_by);

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'k5m6n7o8p9q0';
