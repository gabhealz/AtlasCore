"""Add onboarding briefing fields

Revision ID: 6f8a7b2c1d4e
Revises: 55e6c2f525e3
Create Date: 2026-04-21 21:14:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f8a7b2c1d4e"
down_revision: Union[str, None] = "55e6c2f525e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("onboardings", sa.Column("specialty", sa.String(), nullable=True))
    op.add_column(
        "onboardings",
        sa.Column("target_audience", sa.Text(), nullable=True),
    )
    op.add_column(
        "onboardings",
        sa.Column("differentials", sa.Text(), nullable=True),
    )
    op.add_column(
        "onboardings",
        sa.Column("tone_of_voice", sa.Text(), nullable=True),
    )

    op.execute(
        """
        UPDATE onboardings
        SET
            specialty = 'A definir',
            target_audience = 'A definir',
            differentials = 'A definir',
            tone_of_voice = 'A definir'
        WHERE
            specialty IS NULL
            OR target_audience IS NULL
            OR differentials IS NULL
            OR tone_of_voice IS NULL
        """
    )

    op.alter_column("onboardings", "specialty", nullable=False)
    op.alter_column("onboardings", "target_audience", nullable=False)
    op.alter_column("onboardings", "differentials", nullable=False)
    op.alter_column("onboardings", "tone_of_voice", nullable=False)


def downgrade() -> None:
    op.drop_column("onboardings", "tone_of_voice")
    op.drop_column("onboardings", "differentials")
    op.drop_column("onboardings", "target_audience")
    op.drop_column("onboardings", "specialty")
