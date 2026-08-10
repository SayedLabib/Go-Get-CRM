"""add filing_pipeline final_confirmation_date column

Revision ID: b1c2d3e4f5a6
Revises: a9b1c2d3e4f5
Create Date: 2026-08-10 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a9b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('filing_pipelines', sa.Column('final_confirmation_date', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('filing_pipelines', 'final_confirmation_date')
