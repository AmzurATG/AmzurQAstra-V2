"""add adapted_steps to test_results

Revision ID: 2bd17a756caa
Revises: 0002
Create Date: 2026-03-31 11:32:05.463287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2bd17a756caa'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add adapted_steps column to test_results table
    op.add_column('test_results', sa.Column('adapted_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove adapted_steps column from test_results table
    op.drop_column('test_results', 'adapted_steps')
