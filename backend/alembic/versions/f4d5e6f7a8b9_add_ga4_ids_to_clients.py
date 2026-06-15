"""add ga4 ids to clients

Revision ID: f4d5e6f7a8b9
Revises: f3c4d5e6f7a8
Create Date: 2026-06-15 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4d5e6f7a8b9'
down_revision: Union[str, None] = 'f3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('ga4_property_id', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('ga4_measurement_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'ga4_measurement_id')
    op.drop_column('clients', 'ga4_property_id')
