"""Add asset category and storage url to uploaded assets

Revision ID: 9f2c7a4b1d6e
Revises: 8b3c1d4e6f7a
Create Date: 2026-04-22 15:52:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2c7a4b1d6e"
down_revision: Union[str, None] = "8b3c1d4e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "uploaded_assets",
        sa.Column("asset_category", sa.String(), nullable=True),
    )
    op.add_column(
        "uploaded_assets",
        sa.Column("storage_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("uploaded_assets", "storage_url")
    op.drop_column("uploaded_assets", "asset_category")
