"""add contract fields to clients

Revision ID: e7a1b2c3d4f5
Revises: d3f6b2a8c1e5
Create Date: 2026-06-15 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1b2c3d4f5'
down_revision: Union[str, None] = 'd3f6b2a8c1e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('plan_name', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('external_code', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('document', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('contract_start_date', sa.Date(), nullable=True))
    op.add_column('clients', sa.Column('contract_end_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'contract_end_date')
    op.drop_column('clients', 'contract_start_date')
    op.drop_column('clients', 'document')
    op.drop_column('clients', 'external_code')
    op.drop_column('clients', 'plan_name')
