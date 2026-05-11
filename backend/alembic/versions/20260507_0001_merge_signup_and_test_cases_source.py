"""Merge signup (s1g2n3u4p5v1) and test_cases.source (n8o9p0q1r2s3) branches.

Both revisions shared down_revision m7n8o9p0q1r2. If only n8o9p0q1r2s3 was applied,
`alembic upgrade head` will apply s1g2n3u4p5v1 first (users.is_verified, signup tables).

Revision ID: m3r4g5e6s7g8n9
Revises: s1g2n3u4p5v1, n8o9p0q1r2s3
Create Date: 2026-05-07

"""
from typing import Sequence, Union

from alembic import op


revision: str = "m3r4g5e6s7g8n9"
down_revision: Union[str, Sequence[str], None] = ("s1g2n3u4p5v1", "n8o9p0q1r2s3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
