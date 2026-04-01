"""add original_steps to test_results

Revision ID: 0300da16b3d7
Revises: 2bd17a756caa
Create Date: 2026-03-31 12:48:30.517864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0300da16b3d7'
down_revision: Union[str, None] = '2bd17a756caa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add original_steps column to test_results table
    op.add_column('test_results', sa.Column('original_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove original_steps column from test_results table
    op.drop_column('test_results', 'original_steps')
