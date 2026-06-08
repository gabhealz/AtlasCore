"""create llm_usage_events

Revision ID: d3f6b2a8c1e5
Revises: c2e5a8b1d9f4
Create Date: 2026-06-08 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d3f6b2a8c1e5"
down_revision = "c2e5a8b1d9f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("onboarding_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("web_searches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboardings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_usage_events_id", "llm_usage_events", ["id"], unique=False
    )
    op.create_index(
        "ix_llm_usage_events_onboarding_id",
        "llm_usage_events",
        ["onboarding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_usage_events_onboarding_id", table_name="llm_usage_events"
    )
    op.drop_index("ix_llm_usage_events_id", table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
