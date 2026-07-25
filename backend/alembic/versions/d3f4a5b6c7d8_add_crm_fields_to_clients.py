"""clients.crm_deal_id e clients.crm_payload — cliente que veio do CRM.

Quando um negócio é marcado como ganho no CRM, ele vira cliente aqui como
rascunho. `crm_deal_id` é único justamente pra reentrega do webhook não criar
o mesmo cliente duas vezes; `crm_payload` guarda o retrato que veio junto
(histórico de etapas, comunicações, produto), pra quem for completar o
cadastro ter contexto do que foi vendido.

Revision ID: d3f4a5b6c7d8
Revises: c2e3f4a5b6c7
Create Date: 2026-07-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d3f4a5b6c7d8"
down_revision: Union[str, None] = "c2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("crm_deal_id", sa.String(), nullable=True))
    op.add_column(
        "clients",
        sa.Column("crm_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_unique_constraint("uq_clients_crm_deal_id", "clients", ["crm_deal_id"])


def downgrade() -> None:
    op.drop_constraint("uq_clients_crm_deal_id", "clients", type_="unique")
    op.drop_column("clients", "crm_payload")
    op.drop_column("clients", "crm_deal_id")
