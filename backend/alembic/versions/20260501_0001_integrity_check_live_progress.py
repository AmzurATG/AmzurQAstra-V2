"""Add live_progress JSONB to integrity_check_results for cross-worker polling.

Revision ID: m7n8o9p0q1r2
Revises: l6n7o8p9q0r1
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m7n8o9p0q1r2"
down_revision: Union[str, None] = "l6n7o8p9q0r1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "integrity_check_results",
        sa.Column("live_progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("integrity_check_results", "live_progress")
