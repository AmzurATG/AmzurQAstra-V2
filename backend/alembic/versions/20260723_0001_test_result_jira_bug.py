"""Add jira_bug_key and jira_bug_url to test_results.

Revision ID: j1r2a3b4u5g6
Revises: a1c2c3u4r5a6
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j1r2a3b4u5g6"
down_revision: Union[str, None] = "c0g1n2i3t4v5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_results",
        sa.Column("jira_bug_key", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "test_results",
        sa.Column("jira_bug_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_results", "jira_bug_url")
    op.drop_column("test_results", "jira_bug_key")
