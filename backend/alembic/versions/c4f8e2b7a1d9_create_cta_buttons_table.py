"""Create cta buttons table

Revision ID: c4f8e2b7a1d9
Revises: 9f2c7a4b1d6e
Create Date: 2026-04-22 16:31:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4f8e2b7a1d9"
down_revision: Union[str, None] = "9f2c7a4b1d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cta_buttons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("onboarding_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("button_text", sa.String(), nullable=False),
        sa.Column("css_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboardings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "onboarding_id",
            "css_id",
            name="uq_cta_buttons_onboarding_css_id",
        ),
    )
    op.create_index(op.f("ix_cta_buttons_id"), "cta_buttons", ["id"], unique=False)
    op.create_index(
        op.f("ix_cta_buttons_onboarding_id"),
        "cta_buttons",
        ["onboarding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cta_buttons_onboarding_id"), table_name="cta_buttons")
    op.drop_index(op.f("ix_cta_buttons_id"), table_name="cta_buttons")
    op.drop_table("cta_buttons")
