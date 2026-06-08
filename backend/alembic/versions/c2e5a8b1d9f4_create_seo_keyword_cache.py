"""create seo_keyword_cache

Revision ID: c2e5a8b1d9f4
Revises: b1d4f7a9c2e3
Create Date: 2026-06-08 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2e5a8b1d9f4"
down_revision = "b1d4f7a9c2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_keyword_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(), nullable=False),
        sa.Column("location_code", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(), nullable=False),
        sa.Column("avg_monthly_searches", sa.Integer(), nullable=True),
        sa.Column("cpc", sa.Numeric(10, 2), nullable=True),
        sa.Column("competition", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "queried_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "keyword",
            "location_code",
            "language_code",
            name="uq_seo_keyword_cache_keyword_loc_lang",
        ),
    )
    op.create_index(
        "ix_seo_keyword_cache_id", "seo_keyword_cache", ["id"], unique=False
    )
    op.create_index(
        "ix_seo_keyword_cache_keyword",
        "seo_keyword_cache",
        ["keyword"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_seo_keyword_cache_keyword", table_name="seo_keyword_cache")
    op.drop_index("ix_seo_keyword_cache_id", table_name="seo_keyword_cache")
    op.drop_table("seo_keyword_cache")
