"""create tintim_events

Revision ID: f1a2b3c4d5e6
Revises: e7a1b2c3d4f5
Create Date: 2026-06-15 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7a1b2c3d4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tintim_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('integration_id', sa.Integer(), nullable=True),
        sa.Column('external_event_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('value', sa.Numeric(10, 2), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('dedupe_key', sa.String(), nullable=False),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['integration_id'], ['integration_settings.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedupe_key', name='uq_tintim_event_dedupe'),
    )
    op.create_index(op.f('ix_tintim_events_client_id'), 'tintim_events', ['client_id'], unique=False)
    op.create_index(op.f('ix_tintim_events_week_start'), 'tintim_events', ['week_start'], unique=False)
    op.create_index(op.f('ix_tintim_events_id'), 'tintim_events', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tintim_events_id'), table_name='tintim_events')
    op.drop_index(op.f('ix_tintim_events_week_start'), table_name='tintim_events')
    op.drop_index(op.f('ix_tintim_events_client_id'), table_name='tintim_events')
    op.drop_table('tintim_events')
