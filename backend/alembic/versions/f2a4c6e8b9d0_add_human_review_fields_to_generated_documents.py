"""Add human review fields to generated documents

Revision ID: f2a4c6e8b9d0
Revises: e4f1c2d3b5a6
Create Date: 2026-04-23 23:18:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a4c6e8b9d0"
down_revision: Union[str, None] = "e4f1c2d3b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_documents",
        sa.Column(
            "review_status",
            sa.String(),
            nullable=False,
            server_default="APPROVED",
        ),
    )
    op.add_column(
        "generated_documents",
        sa.Column("review_feedback", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_documents",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_documents", "reviewed_at")
    op.drop_column("generated_documents", "review_feedback")
    op.drop_column("generated_documents", "review_status")
