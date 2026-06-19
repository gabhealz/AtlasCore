"""security: User.is_active, GeneratedDocument.is_current versioning, ON DELETE CASCADE on all FKs, metric_snapshots indexes

Revision ID: a0b1c2d3e4f5
Revises: f5e6f7a8b9c0
Create Date: 2026-06-18 14:00:00.000000

Covers:
- CRIT-6: users.is_active (soft-disable users without DB deletion)
- H11:    generated_documents.is_current (preserve document version history on pipeline rerun)
          + partial unique index replacing hard unique constraint
- CRIT-7: ON DELETE CASCADE on all FK relationships (metric_snapshots, campaign_snapshots,
          integration_settings, sync_logs, tintim_events, generated_documents,
          pipeline_events, llm_usage_events, uploaded_assets, cta_buttons)
- Perf:   composite index on metric_snapshots(client_id, week_start) for dashboard queries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. users.is_active ──────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # ── 2. generated_documents.is_current + version-aware unique index ───────
    op.add_column(
        "generated_documents",
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Drop the hard unique constraint — multiple versions of the same
    # (onboarding_id, document_kind) pair now allowed; only one can be current.
    op.drop_constraint(
        "uq_generated_documents_onboarding_kind",
        "generated_documents",
        type_="unique",
    )
    # Partial unique index: at most one current document per (onboarding, kind).
    op.create_index(
        "ix_generated_documents_current_kind",
        "generated_documents",
        ["onboarding_id", "document_kind"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # ── 3. ON DELETE CASCADE on all FK columns ───────────────────────────────
    # FK names are PostgreSQL auto-generated (tablename_colname_fkey).

    # metric_snapshots.client_id → clients.id
    op.drop_constraint(
        "metric_snapshots_client_id_fkey", "metric_snapshots", type_="foreignkey"
    )
    op.create_foreign_key(
        None, "metric_snapshots", "clients", ["client_id"], ["id"], ondelete="CASCADE"
    )

    # campaign_snapshots.client_id → clients.id
    op.drop_constraint(
        "campaign_snapshots_client_id_fkey", "campaign_snapshots", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "campaign_snapshots",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # integration_settings.client_id → clients.id
    op.drop_constraint(
        "integration_settings_client_id_fkey",
        "integration_settings",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "integration_settings",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # sync_logs.client_id → clients.id
    op.drop_constraint(
        "sync_logs_client_id_fkey", "sync_logs", type_="foreignkey"
    )
    op.create_foreign_key(
        None, "sync_logs", "clients", ["client_id"], ["id"], ondelete="CASCADE"
    )

    # tintim_events.client_id → clients.id
    op.drop_constraint(
        "tintim_events_client_id_fkey", "tintim_events", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "tintim_events",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # tintim_events.integration_id → integration_settings.id (SET NULL safer here)
    op.drop_constraint(
        "tintim_events_integration_id_fkey", "tintim_events", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "tintim_events",
        "integration_settings",
        ["integration_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # generated_documents.onboarding_id → onboardings.id
    op.drop_constraint(
        "generated_documents_onboarding_id_fkey",
        "generated_documents",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "generated_documents",
        "onboardings",
        ["onboarding_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # pipeline_events.onboarding_id → onboardings.id
    op.drop_constraint(
        "pipeline_events_onboarding_id_fkey", "pipeline_events", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "pipeline_events",
        "onboardings",
        ["onboarding_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # llm_usage_events.onboarding_id → onboardings.id
    op.drop_constraint(
        "llm_usage_events_onboarding_id_fkey", "llm_usage_events", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "llm_usage_events",
        "onboardings",
        ["onboarding_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # uploaded_assets.onboarding_id → onboardings.id
    op.drop_constraint(
        "uploaded_assets_onboarding_id_fkey", "uploaded_assets", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "uploaded_assets",
        "onboardings",
        ["onboarding_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # cta_buttons.onboarding_id → onboardings.id
    op.drop_constraint(
        "cta_buttons_onboarding_id_fkey", "cta_buttons", type_="foreignkey"
    )
    op.create_foreign_key(
        None,
        "cta_buttons",
        "onboardings",
        ["onboarding_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── 4. Performance indexes on metric_snapshots ───────────────────────────
    op.create_index(
        "ix_metric_snapshots_week_start",
        "metric_snapshots",
        ["week_start"],
    )
    op.create_index(
        "ix_metric_snapshots_client_week",
        "metric_snapshots",
        ["client_id", "week_start"],
    )


def downgrade() -> None:
    # Performance indexes
    op.drop_index("ix_metric_snapshots_client_week", table_name="metric_snapshots")
    op.drop_index("ix_metric_snapshots_week_start", table_name="metric_snapshots")

    # Restore original FK constraints (without CASCADE)
    for table, col, ref_table, ref_col in [
        ("cta_buttons", "onboarding_id", "onboardings", "id"),
        ("uploaded_assets", "onboarding_id", "onboardings", "id"),
        ("llm_usage_events", "onboarding_id", "onboardings", "id"),
        ("pipeline_events", "onboarding_id", "onboardings", "id"),
        ("generated_documents", "onboarding_id", "onboardings", "id"),
        ("sync_logs", "client_id", "clients", "id"),
        ("integration_settings", "client_id", "clients", "id"),
        ("campaign_snapshots", "client_id", "clients", "id"),
        ("metric_snapshots", "client_id", "clients", "id"),
    ]:
        # Drop the CASCADE FK (auto-named by SQLAlchemy during upgrade)
        # and recreate without cascade. Names will differ; use batch mode.
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"{table}_{col}_fkey", type_="foreignkey")
            batch_op.create_foreign_key(None, ref_table, [col], [ref_col])

    # Restore tintim_events FKs
    with op.batch_alter_table("tintim_events") as batch_op:
        batch_op.drop_constraint("tintim_events_client_id_fkey", type_="foreignkey")
        batch_op.drop_constraint(
            "tintim_events_integration_id_fkey", type_="foreignkey"
        )
        batch_op.create_foreign_key(None, "clients", ["client_id"], ["id"])
        batch_op.create_foreign_key(
            None, "integration_settings", ["integration_id"], ["id"]
        )

    # Restore generated_documents unique constraint
    op.drop_index(
        "ix_generated_documents_current_kind", table_name="generated_documents"
    )
    op.create_unique_constraint(
        "uq_generated_documents_onboarding_kind",
        "generated_documents",
        ["onboarding_id", "document_kind"],
    )

    # Remove new columns
    op.drop_column("generated_documents", "is_current")
    op.drop_column("users", "is_active")
