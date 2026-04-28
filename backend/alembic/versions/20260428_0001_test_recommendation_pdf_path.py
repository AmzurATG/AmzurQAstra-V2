"""add pdf_path to test_recommendation_runs

Revision ID: l6n7o8p9q0r1
Revises: k5m6n7o8p9q0
Create Date: 2026-04-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l6n7o8p9q0r1"
down_revision: Union[str, None] = "k5m6n7o8p9q0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_recommendation_runs",
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_recommendation_runs", "pdf_path")
