"""add test_cases.case_number per-project sequence

Revision ID: h1b2c3d4e5f6
Revises: g9a0b1c2d3e4
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1b2c3d4e5f6"
down_revision: Union[str, None] = "g9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column("case_number", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE test_cases AS t
        SET case_number = s.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS rn
            FROM test_cases
        ) AS s
        WHERE t.id = s.id
        """
    )
    op.alter_column("test_cases", "case_number", nullable=False)
    op.create_unique_constraint(
        "uq_test_cases_project_case_number",
        "test_cases",
        ["project_id", "case_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_test_cases_project_case_number",
        "test_cases",
        type_="unique",
    )
    op.drop_column("test_cases", "case_number")
