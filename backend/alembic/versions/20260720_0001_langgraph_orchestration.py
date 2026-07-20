"""Add test_run_groups and orchestration columns on test_results.

Revision ID: l1g2g3r4p5h6
Revises: w1o2r3k4e5r6
Create Date: 2026-07-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "l1g2g3r4p5h6"
down_revision: Union[str, None] = "w1o2r3k4e5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_run_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("phase_order", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("case_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("case_phases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("merged_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("shared_login", sa.Boolean(), nullable=True),
        sa.Column("lane_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="testrungroupstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_run_groups_test_run_id", "test_run_groups", ["test_run_id"])

    op.add_column("test_results", sa.Column("group_id", sa.String(length=64), nullable=True))
    op.add_column("test_results", sa.Column("ai_modified", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index("ix_test_results_group_id", "test_results", ["group_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_test_results_group_id", table_name="test_results")
    op.drop_column("test_results", "ai_modified")
    op.drop_column("test_results", "group_id")
    op.drop_index("ix_test_run_groups_test_run_id", table_name="test_run_groups")
    op.drop_table("test_run_groups")
    op.execute("DROP TYPE IF EXISTS testrungroupstatus")
