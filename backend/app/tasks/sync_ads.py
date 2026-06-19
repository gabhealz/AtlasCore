"""Background tasks for syncing ad platform data.

Uses SQLAlchemy Core (text SQL) instead of ORM to avoid mapper initialization
issues in Celery prefork worker processes, where SQLAlchemy relationship string
references (e.g. "Client") may not be resolvable after fork.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from app.core.encryption import decrypt_value
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _get_engine():
    """Create a synchronous psycopg2 engine (one per task call)."""
    from sqlalchemy import create_engine
    from app.core.config import settings

    sync_url = (
        settings.DATABASE_URL
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql://", "postgresql+psycopg2://")
    )
    return create_engine(sync_url, pool_pre_ping=True)


# ─── sweep ────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.sync_ads.sync_all_clients")
def sync_all_clients():
    """Enqueue per-client sync tasks for every active integration.
    Called by Celery Beat every 6 hours.
    """
    logger.info("Starting sync_all_clients sweep...")

    from sqlalchemy import text

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT client_id, platform,
                       encrypted_access_token, encrypted_refresh_token
                FROM integration_settings
                WHERE is_active = true
                  AND platform IN ('meta', 'google', 'ga4')
                  AND (
                    encrypted_access_token IS NOT NULL
                    OR encrypted_refresh_token IS NOT NULL
                  )
            """)).fetchall()

        enqueued = 0
        for row in rows:
            sync_client_ads.delay(row.client_id, row.platform)
            enqueued += 1

        logger.info("sync_all_clients completed — enqueued %d tasks.", enqueued)
        return {"status": "ok", "enqueued": enqueued}

    except Exception as exc:
        logger.error("sync_all_clients failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


# ─── per-client sync ──────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.tasks.sync_ads.sync_client_ads")
def sync_client_ads(self, client_id: int, platform: str):
    """Sync ad data for a single client on a specific platform."""
    logger.info(
        "sync_client_ads start client_id=%s platform=%s task=%s",
        client_id, platform, self.request.id,
    )

    from sqlalchemy import text

    engine = _get_engine()
    target_date = date.today() - timedelta(days=1)

    try:
        # Load integration via Core SQL (no ORM mapper needed)
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT id, account_id,
                       encrypted_access_token, encrypted_refresh_token
                FROM integration_settings
                WHERE client_id = :cid
                  AND platform = :platform
                  AND is_active = true
                LIMIT 1
            """), {"cid": client_id, "platform": platform}).fetchone()

        if not row:
            logger.warning("No integration for client_id=%s platform=%s", client_id, platform)
            return {"client_id": client_id, "platform": platform, "status": "no_integration"}

        integration_id = row.id
        account_id = row.account_id or ""
        access_token = decrypt_value(row.encrypted_access_token) if row.encrypted_access_token else None
        refresh_token = decrypt_value(row.encrypted_refresh_token) if row.encrypted_refresh_token else None

        # ── fetch from platform ───────────────────────────────────────────────
        data: dict = {}

        if platform == "meta":
            if not access_token:
                raise ValueError("Meta Ads: access token não configurado.")
            from app.integrations.meta_ads import fetch_daily_insights
            data = fetch_daily_insights(access_token, account_id, target_date)

        elif platform == "google":
            token = refresh_token or access_token
            if not token:
                raise ValueError("Google Ads: refresh token não configurado.")
            from app.integrations.google_ads import fetch_daily_insights
            data = fetch_daily_insights(token, account_id, target_date)

        elif platform == "ga4":
            if not access_token:
                raise ValueError("GA4: Service Account JSON não configurado.")
            from app.integrations.ga4 import fetch_daily_insights
            data = fetch_daily_insights(access_token, account_id, target_date)

        else:
            return {"client_id": client_id, "platform": platform, "status": "unknown_platform"}

        # ── upsert MetricSnapshot via Core SQL ────────────────────────────────
        _upsert_metric_snapshot_core(engine, client_id, platform, target_date, data)

        # ── update integration status + log ───────────────────────────────────
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE integration_settings
                SET last_sync_at = :now, sync_status = 'success', updated_at = :now
                WHERE id = :iid
            """), {"now": now, "iid": integration_id})
            conn.execute(text("""
                INSERT INTO sync_logs (client_id, platform, status, created_at)
                VALUES (:cid, :platform, 'success', :now)
            """), {"cid": client_id, "platform": platform, "now": now})

        logger.info("sync_client_ads done client_id=%s platform=%s data=%s", client_id, platform, data)
        return {"client_id": client_id, "platform": platform, "status": "success", "data": data}

    except Exception as exc:
        logger.error("sync_client_ads FAILED client_id=%s platform=%s: %s", client_id, platform, exc)
        try:
            now = datetime.now(timezone.utc)
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE integration_settings
                    SET sync_status = 'failed', updated_at = :now
                    WHERE client_id = :cid AND platform = :platform
                """), {"now": now, "cid": client_id, "platform": platform})
                conn.execute(text("""
                    INSERT INTO sync_logs (client_id, platform, status, error_message, created_at)
                    VALUES (:cid, :platform, 'failed', :err, :now)
                """), {"cid": client_id, "platform": platform, "err": str(exc)[:1000], "now": now})
        except Exception:
            pass
        return {"client_id": client_id, "platform": platform, "status": "failed", "error": str(exc)}


# ─── helpers ──────────────────────────────────────────────────────────────────

def _upsert_metric_snapshot_core(engine, client_id: int, platform: str, target_date: date, data: dict):
    """Upsert MetricSnapshot keyed by (client_id, week_start, source) using Core SQL."""
    from sqlalchemy import text

    week_start = target_date - timedelta(days=target_date.weekday())
    now = datetime.now(timezone.utc)

    if platform in ("meta", "google"):
        spend = float(data.get("spend", 0) or 0)
        impressions = int(data.get("impressions", 0) or 0)
        clicks = int(data.get("clicks", 0) or 0)
        conversions = int(data.get("leads" if platform == "meta" else "conversions", 0) or 0)
        cpc = float(data.get("cpc", 0) or 0) or None
        ctr = float(data.get("ctr", 0) or 0) or None

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO metric_snapshots
                    (client_id, week_start, source, ad_spend, impressions, clicks, cpc, ctr, conversions, created_at, updated_at)
                VALUES
                    (:cid, :ws, :src, :spend, :imp, :clicks, :cpc, :ctr, :conv, :now, :now)
                ON CONFLICT (client_id, week_start, source) DO UPDATE SET
                    ad_spend    = metric_snapshots.ad_spend    + EXCLUDED.ad_spend,
                    impressions = metric_snapshots.impressions + EXCLUDED.impressions,
                    clicks      = metric_snapshots.clicks      + EXCLUDED.clicks,
                    conversions = metric_snapshots.conversions + EXCLUDED.conversions,
                    cpc         = COALESCE(EXCLUDED.cpc, metric_snapshots.cpc),
                    ctr         = COALESCE(EXCLUDED.ctr, metric_snapshots.ctr),
                    updated_at  = :now
            """), {
                "cid": client_id, "ws": week_start, "src": platform,
                "spend": spend, "imp": impressions, "clicks": clicks,
                "cpc": cpc, "ctr": ctr, "conv": conversions, "now": now,
            })

    elif platform == "ga4":
        lp_sessions = int(data.get("lp_sessions") or data.get("sessions") or 0)
        ga4_conv = int(data.get("conversions", 0) or 0)

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO metric_snapshots
                    (client_id, week_start, source, lp_sessions, conversions, created_at, updated_at)
                VALUES
                    (:cid, :ws, 'ga4', :lp, :conv, :now, :now)
                ON CONFLICT (client_id, week_start, source) DO UPDATE SET
                    lp_sessions = COALESCE(metric_snapshots.lp_sessions, 0) + EXCLUDED.lp_sessions,
                    conversions = CASE
                        WHEN metric_snapshots.conversions IS NULL OR metric_snapshots.conversions = 0
                        THEN EXCLUDED.conversions
                        ELSE metric_snapshots.conversions
                    END,
                    updated_at = :now
            """), {"cid": client_id, "ws": week_start, "lp": lp_sessions, "conv": ga4_conv, "now": now})
