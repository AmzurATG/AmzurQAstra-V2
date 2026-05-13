-- ============================================
-- Migration: 0002 - Add integrity_check_results table
-- Date: 2026-03-26
-- ============================================

SET search_path TO qastraschema;

CREATE TABLE IF NOT EXISTS integrity_check_results (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    run_id      VARCHAR(64) NOT NULL UNIQUE,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    app_url     VARCHAR(500) NOT NULL,

    app_reachable    BOOLEAN,
    login_successful BOOLEAN,
    overall_status   VARCHAR(20),

    steps_total   INTEGER DEFAULT 0,
    steps_passed  INTEGER DEFAULT 0,
    steps_failed  INTEGER DEFAULT 0,

    summary       TEXT,
    error_message TEXT,
    steps_data    JSONB,
    screenshots   JSONB,

    duration_ms   INTEGER,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_integrity_check_results_project_id
    ON integrity_check_results(project_id);
CREATE INDEX IF NOT EXISTS ix_integrity_check_results_run_id
    ON integrity_check_results(run_id);

-- Stamp alembic version
UPDATE alembic_version SET version_num = '0002';
