"""create ibge_municipios

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ibge_municipios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('uf_sigla', sa.String(length=2), nullable=False),
        sa.Column('uf_id', sa.Integer(), nullable=True),
        sa.Column('uf_nome', sa.String(), nullable=True),
        sa.Column('is_capital', sa.Boolean(), nullable=True),
        sa.Column('populacao', sa.BigInteger(), nullable=True),
        sa.Column('populacao_ano', sa.Integer(), nullable=True),
        sa.Column('classificacao_porte', sa.String(), nullable=True),
        sa.Column('pyramid_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pyramid_ano', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ibge_municipios_id'), 'ibge_municipios', ['id'], unique=False)
    op.create_index(op.f('ix_ibge_municipios_uf_sigla'), 'ibge_municipios', ['uf_sigla'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ibge_municipios_uf_sigla'), table_name='ibge_municipios')
    op.drop_index(op.f('ix_ibge_municipios_id'), table_name='ibge_municipios')
    op.drop_table('ibge_municipios')
