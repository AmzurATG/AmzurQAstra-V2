"""Add worker_id to test_results for concurrent execution tracing.

Revision ID: w1o2r3k4e5r6
Revises: m3r4g5e6s7g8n9
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w1o2r3k4e5r6"
down_revision: Union[str, None] = "m3r4g5e6s7g8n9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("test_results", sa.Column("worker_id", sa.Integer(), nullable=True))
    op.create_index("ix_test_results_worker_id", "test_results", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_test_results_worker_id", table_name="test_results")
    op.drop_column("test_results", "worker_id")
