"""Add test_cases.source: manual | ai | csv

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, None] = "m7n8o9p0q1r2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column(
            "source",
            sa.String(16),
            nullable=False,
            server_default="manual",
        ),
    )
    op.execute("UPDATE test_cases SET source = 'ai' WHERE is_generated = true")


def downgrade() -> None:
    op.drop_column("test_cases", "source")
