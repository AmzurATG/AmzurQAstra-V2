"""Add integrity_check_results table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-26

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
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
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS integrity_check_results;")
