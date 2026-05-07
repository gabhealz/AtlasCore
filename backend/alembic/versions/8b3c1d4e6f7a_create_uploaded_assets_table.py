"""Create uploaded assets table

Revision ID: 8b3c1d4e6f7a
Revises: 7c3d1a4e9b2f
Create Date: 2026-04-21 21:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b3c1d4e6f7a"
down_revision: Union[str, None] = "7c3d1a4e9b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uploaded_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("onboarding_id", sa.Integer(), nullable=False),
        sa.Column("asset_kind", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboardings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        op.f("ix_uploaded_assets_id"), "uploaded_assets", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_uploaded_assets_onboarding_id"),
        "uploaded_assets",
        ["onboarding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_uploaded_assets_onboarding_id"), table_name="uploaded_assets")
    op.drop_index(op.f("ix_uploaded_assets_id"), table_name="uploaded_assets")
    op.drop_table("uploaded_assets")
