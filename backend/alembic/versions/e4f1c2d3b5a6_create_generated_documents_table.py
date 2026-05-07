"""Create generated documents table

Revision ID: e4f1c2d3b5a6
Revises: d7c9b1e4a2f6
Create Date: 2026-04-23 18:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f1c2d3b5a6"
down_revision: Union[str, None] = "d7c9b1e4a2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("onboarding_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("document_kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboardings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "onboarding_id",
            "document_kind",
            name="uq_generated_documents_onboarding_kind",
        ),
    )
    op.create_index(
        op.f("ix_generated_documents_id"),
        "generated_documents",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_onboarding_id"),
        "generated_documents",
        ["onboarding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_generated_documents_onboarding_id"),
        table_name="generated_documents",
    )
    op.drop_index(op.f("ix_generated_documents_id"), table_name="generated_documents")
    op.drop_table("generated_documents")
