"""Add ui_discovery_runs table and test_cases UI metadata columns.

Revision ID: u1d2i3s4c5o6
Revises: p1q2r3s4t5u6
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "u1d2i3s4c5o6"
down_revision: Union[str, None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ui_discovery_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("platform", sa.String(length=20), nullable=False, server_default="web"),
        sa.Column("actor_role", sa.String(length=32), nullable=False, server_default="end_user"),
        sa.Column("app_url", sa.String(length=500), nullable=False),
        sa.Column("inventory_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("screenshots", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("source_integrity_run_id", sa.Integer(), nullable=True),
        sa.Column("live_progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_integrity_run_id"], ["integrity_check_results.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_ui_discovery_runs_project_id", "ui_discovery_runs", ["project_id"])
    op.create_index("ix_ui_discovery_runs_run_id", "ui_discovery_runs", ["run_id"])

    op.add_column("projects", sa.Column("latest_ui_discovery_run_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_projects_latest_ui_discovery_run_id",
        "projects",
        "ui_discovery_runs",
        ["latest_ui_discovery_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("test_cases", sa.Column("platform", sa.String(length=16), nullable=True))
    op.add_column("test_cases", sa.Column("actor_role", sa.String(length=32), nullable=True))
    op.add_column("test_cases", sa.Column("ui_page_ref", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("test_cases", "ui_page_ref")
    op.drop_column("test_cases", "actor_role")
    op.drop_column("test_cases", "platform")
    op.drop_constraint("fk_projects_latest_ui_discovery_run_id", "projects", type_="foreignkey")
    op.drop_column("projects", "latest_ui_discovery_run_id")
    op.drop_index("ix_ui_discovery_runs_run_id", table_name="ui_discovery_runs")
    op.drop_index("ix_ui_discovery_runs_project_id", table_name="ui_discovery_runs")
    op.drop_table("ui_discovery_runs")
