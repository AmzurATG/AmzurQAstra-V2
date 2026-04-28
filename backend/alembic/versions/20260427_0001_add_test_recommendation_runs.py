"""add test_recommendation_runs

Revision ID: k5m6n7o8p9q0
Revises: j3k4l5m6n7o8
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k5m6n7o8p9q0"
down_revision: Union[str, None] = "j3k4l5m6n7o8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_recommendation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_recommendation_runs_project_id", "test_recommendation_runs", ["project_id"])
    op.create_index(
        "ix_test_recommendation_runs_requirement_id", "test_recommendation_runs", ["requirement_id"]
    )
    op.create_index("ix_test_recommendation_runs_created_by", "test_recommendation_runs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_test_recommendation_runs_created_by", table_name="test_recommendation_runs")
    op.drop_index("ix_test_recommendation_runs_requirement_id", table_name="test_recommendation_runs")
    op.drop_index("ix_test_recommendation_runs_project_id", table_name="test_recommendation_runs")
    op.drop_table("test_recommendation_runs")
