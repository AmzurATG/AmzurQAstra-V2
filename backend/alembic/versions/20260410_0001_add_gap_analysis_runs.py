"""add gap_analysis_runs

Revision ID: g9a0b1c2d3e4
Revises: f8e9a1b2c3d4
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "g9a0b1c2d3e4"
down_revision: Union[str, None] = "f8e9a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gap_analysis_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gap_analysis_runs_project_id", "gap_analysis_runs", ["project_id"])
    op.create_index("ix_gap_analysis_runs_requirement_id", "gap_analysis_runs", ["requirement_id"])
    op.create_index("ix_gap_analysis_runs_created_by", "gap_analysis_runs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_gap_analysis_runs_created_by", table_name="gap_analysis_runs")
    op.drop_index("ix_gap_analysis_runs_requirement_id", table_name="gap_analysis_runs")
    op.drop_index("ix_gap_analysis_runs_project_id", table_name="gap_analysis_runs")
    op.drop_table("gap_analysis_runs")
