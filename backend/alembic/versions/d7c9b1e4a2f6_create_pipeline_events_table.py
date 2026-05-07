"""Create pipeline events table

Revision ID: d7c9b1e4a2f6
Revises: c4f8e2b7a1d9
Create Date: 2026-04-23 11:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7c9b1e4a2f6"
down_revision: Union[str, None] = "c4f8e2b7a1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("onboarding_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=False),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboardings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pipeline_events_id"), "pipeline_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_pipeline_events_onboarding_id"),
        "pipeline_events",
        ["onboarding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pipeline_events_onboarding_id"), table_name="pipeline_events")
    op.drop_index(op.f("ix_pipeline_events_id"), table_name="pipeline_events")
    op.drop_table("pipeline_events")
