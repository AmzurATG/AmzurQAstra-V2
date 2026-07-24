"""Add parent_group_id to test_run_groups for semantic sub-grouping.

Revision ID: a1c2c3u4r5a6
Revises: l1g2g3r4p5h6
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1c2c3u4r5a6"
down_revision: Union[str, None] = "l1g2g3r4p5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_run_groups",
        sa.Column("parent_group_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_test_run_groups_parent_group_id",
        "test_run_groups",
        ["parent_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_test_run_groups_parent_group_id", table_name="test_run_groups")
    op.drop_column("test_run_groups", "parent_group_id")
