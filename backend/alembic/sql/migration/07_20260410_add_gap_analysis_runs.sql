-- ============================================
-- Migration: g9a0b1c2d3e4 - Add gap_analysis_runs table
-- Date: 2026-04-10
-- ============================================

SET search_path TO qastraschema;

CREATE TABLE IF NOT EXISTS gap_analysis_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result_json JSONB,
    error_message TEXT,
    pdf_path VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS ix_gap_analysis_runs_project_id ON gap_analysis_runs(project_id);
CREATE INDEX IF NOT EXISTS ix_gap_analysis_runs_requirement_id ON gap_analysis_runs(requirement_id);
CREATE INDEX IF NOT EXISTS ix_gap_analysis_runs_created_by ON gap_analysis_runs(created_by);

-- Stamp alembic version
UPDATE alembic_version SET version_num = 'g9a0b1c2d3e4';
