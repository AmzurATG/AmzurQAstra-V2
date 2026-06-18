"""Add bulk generation: generation_jobs table, test_cases scenario_type/ac_ref,
brd_generated user story source.

Revision ID: p1q2r3s4t5u6
Revises: m3r4g5e6s7g8n9
Create Date: 2026-06-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, Sequence[str], None] = "m3r4g5e6s7g8n9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend enum (PostgreSQL: ADD VALUE is not transactional; run outside tx)
    op.execute("ALTER TYPE userstorysource ADD VALUE IF NOT EXISTS 'brd_generated'")

    # New columns on test_cases
    op.add_column(
        "test_cases",
        sa.Column("scenario_type", sa.String(16), nullable=True, server_default="positive"),
    )
    op.add_column(
        "test_cases",
        sa.Column("ac_ref", sa.String(20), nullable=True),
    )

    # generation_jobs table
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("profile", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("story_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("total_stories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_stories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_story_title", sa.String(500), nullable=True),
        sa.Column("coverage_report_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_generation_jobs_project_id", "generation_jobs", ["project_id"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_status", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_project_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
    op.drop_column("test_cases", "ac_ref")
    op.drop_column("test_cases", "scenario_type")
