"""Allow null onboarding briefing fields for legacy records

Revision ID: 7c3d1a4e9b2f
Revises: 6f8a7b2c1d4e
Create Date: 2026-04-21 21:33:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7c3d1a4e9b2f"
down_revision: Union[str, None] = "6f8a7b2c1d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("onboardings", "specialty", nullable=True)
    op.alter_column("onboardings", "target_audience", nullable=True)
    op.alter_column("onboardings", "differentials", nullable=True)
    op.alter_column("onboardings", "tone_of_voice", nullable=True)

    op.execute(
        """
        UPDATE onboardings
        SET
            specialty = NULL,
            target_audience = NULL,
            differentials = NULL,
            tone_of_voice = NULL
        WHERE
            specialty = 'A definir'
            AND target_audience = 'A definir'
            AND differentials = 'A definir'
            AND tone_of_voice = 'A definir'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE onboardings
        SET
            specialty = COALESCE(specialty, 'A definir'),
            target_audience = COALESCE(target_audience, 'A definir'),
            differentials = COALESCE(differentials, 'A definir'),
            tone_of_voice = COALESCE(tone_of_voice, 'A definir')
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
