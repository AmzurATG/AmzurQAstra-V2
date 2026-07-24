"""Placeholder revision present in some local DBs (cognition / interim).

Revision ID: c0g1n2i3t4v5
Revises: a1c2c3u4r5a6
Create Date: 2026-07-23

No schema changes — keeps alembic history aligned when version_num was
already advanced to this id outside the tracked migration set.
"""
from typing import Sequence, Union

revision: str = "c0g1n2i3t4v5"
down_revision: Union[str, None] = "a1c2c3u4r5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
