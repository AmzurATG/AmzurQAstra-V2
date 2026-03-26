"""Add integrity_check_runs, integrity_check_step_results, auth_sessions tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-24

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    -- ================================================================
    -- AUTH SESSIONS
    -- Stores Fernet-encrypted credentials and OAuth storage state per project.
    -- ================================================================
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id                      SERIAL PRIMARY KEY,
        project_id              INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        created_by              INTEGER REFERENCES users(id),
        auth_type               VARCHAR(30) NOT NULL DEFAULT 'credentials',
        encrypted_credentials   TEXT,
        encrypted_storage_state TEXT,
        is_active               BOOLEAN NOT NULL DEFAULT TRUE,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_auth_sessions_project ON auth_sessions(project_id);
    CREATE INDEX IF NOT EXISTS idx_auth_sessions_active  ON auth_sessions(project_id, is_active) WHERE is_active = TRUE;

    -- ================================================================
    -- INTEGRITY CHECK RUNS
    -- One row per integrity check execution.
    -- ================================================================
    CREATE TABLE IF NOT EXISTS integrity_check_runs (
        id                  SERIAL PRIMARY KEY,
        project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        triggered_by        INTEGER REFERENCES users(id),
        status              VARCHAR(20) NOT NULL DEFAULT 'pending',
        app_url             VARCHAR(500) NOT NULL,
        app_reachable       BOOLEAN,
        login_successful    BOOLEAN,
        browser_engine      VARCHAR(30) NOT NULL DEFAULT 'playwright',
        auth_method         VARCHAR(30) NOT NULL DEFAULT 'none',
        test_cases_total    INTEGER DEFAULT 0,
        test_cases_passed   INTEGER DEFAULT 0,
        test_cases_failed   INTEGER DEFAULT 0,
        duration_ms         INTEGER,
        error               TEXT,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_ic_runs_project ON integrity_check_runs(project_id);
    CREATE INDEX IF NOT EXISTS idx_ic_runs_status  ON integrity_check_runs(project_id, status);

    -- ================================================================
    -- INTEGRITY CHECK STEP RESULTS
    -- One row per executed test step within a run.
    -- ================================================================
    CREATE TABLE IF NOT EXISTS integrity_check_step_results (
        id                   SERIAL PRIMARY KEY,
        run_id               INTEGER NOT NULL REFERENCES integrity_check_runs(id) ON DELETE CASCADE,
        test_case_id         INTEGER REFERENCES test_cases(id),
        test_case_title      VARCHAR(500),
        test_case_status     VARCHAR(20),
        test_case_duration_ms INTEGER,
        step_number          INTEGER NOT NULL,
        action               VARCHAR(50),
        description          TEXT,
        status               VARCHAR(20) NOT NULL DEFAULT 'pending',
        error                TEXT,
        screenshot_path      VARCHAR(500),
        llm_diagnosis        TEXT,
        duration_ms          INTEGER,
        created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_ic_steps_run ON integrity_check_step_results(run_id);
    """)

    # Apply updated_at auto-trigger to all three new tables
    for table in ("auth_sessions", "integrity_check_runs", "integrity_check_step_results"):
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS integrity_check_step_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS integrity_check_runs CASCADE;")
    op.execute("DROP TABLE IF EXISTS auth_sessions CASCADE;")
