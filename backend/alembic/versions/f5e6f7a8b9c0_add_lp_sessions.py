"""add lp_sessions to metric_snapshots

Revision ID: f5e6f7a8b9c0
Revises: f4d5e6f7a8b9
Create Date: 2026-06-15 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5e6f7a8b9c0'
down_revision: Union[str, None] = 'f4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('metric_snapshots', sa.Column('lp_sessions', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('metric_snapshots', 'lp_sessions')
