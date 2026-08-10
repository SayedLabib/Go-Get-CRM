"""add task completed_date and actual_hours columns

Revision ID: a9b1c2d3e4f5
Revises: b7c8d9e0f1a2
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b1c2d3e4f5'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('completed_date', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('actual_hours', sa.Numeric(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'actual_hours')
    op.drop_column('tasks', 'completed_date')
