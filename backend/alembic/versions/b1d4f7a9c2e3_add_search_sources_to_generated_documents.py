"""add search_sources to generated_documents

Revision ID: b1d4f7a9c2e3
Revises: 7166efd789de
Create Date: 2026-06-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1d4f7a9c2e3"
down_revision = "7166efd789de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generated_documents",
        sa.Column("search_sources", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_documents", "search_sources")
