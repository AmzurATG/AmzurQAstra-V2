"""add test_runs.run_number per-project sequence

Revision ID: j3k4l5m6n7o8
Revises: h1b2c3d4e5f6
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j3k4l5m6n7o8"
down_revision: Union[str, None] = "h1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_runs",
        sa.Column("run_number", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE test_runs AS t
        SET run_number = s.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS rn
            FROM test_runs
        ) AS s
        WHERE t.id = s.id
        """
    )
    op.alter_column("test_runs", "run_number", nullable=False)
    op.create_unique_constraint(
        "uq_test_runs_project_run_number",
        "test_runs",
        ["project_id", "run_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_test_runs_project_run_number",
        "test_runs",
        type_="unique",
    )
    op.drop_column("test_runs", "run_number")
