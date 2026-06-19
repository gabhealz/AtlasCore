"""Background tasks for syncing ad platform data.

These are the REAL implementations that connect to Meta Ads, Google Ads,
and GA4 APIs using per-client encrypted credentials.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_value
from app.models.client import Client  # noqa: F401 — força resolução do mapper Client↔IntegrationSetting
from app.models.integration_setting import IntegrationSetting
from app.models.metric_snapshot import MetricSnapshot
from app.models.sync_log import SyncLog
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _get_sync_db_session():
    """Create a synchronous DB session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    # Convert async URL to sync URL
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace(
        "postgresql://", "postgresql+psycopg2://"
    )

    engine = create_engine(sync_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(bind=True, name="app.tasks.sync_ads.sync_client_ads")
def sync_client_ads(self, client_id: int, platform: str):
    """Sync ad data for a single client on a specific platform.

    This is the unit of work — called by sync_all_clients for each
    active integration.
    """
    logger.info(
        "Starting sync for client_id=%s platform=%s task_id=%s",
        client_id,
        platform,
        self.request.id,
    )

    db = _get_sync_db_session()
    target_date = date.today() - timedelta(days=1)

    try:
        # Load integration settings
        integration = db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.client_id == client_id,
                IntegrationSetting.platform == platform,
                IntegrationSetting.is_active == True,
            )
        ).scalars().first()

        if not integration:
            logger.warning(
                "No active integration found for client_id=%s platform=%s",
                client_id,
                platform,
            )
            return {"client_id": client_id, "platform": platform, "status": "no_integration"}

        # Decrypt tokens
        access_token = (
            decrypt_value(integration.encrypted_access_token)
            if integration.encrypted_access_token
            else None
        )
        refresh_token = (
            decrypt_value(integration.encrypted_refresh_token)
            if integration.encrypted_refresh_token
            else None
        )
        account_id = integration.account_id or ""

        # Fetch data based on platform
        result = {}

        if platform == "meta":
            if not access_token:
                raise ValueError("Meta Ads: access token não configurado.")
            from app.integrations.meta_ads import fetch_daily_insights
            result = fetch_daily_insights(access_token, account_id, target_date)

        elif platform == "google":
            token = refresh_token or access_token
            if not token:
                raise ValueError("Google Ads: refresh token não configurado.")
            from app.integrations.google_ads import fetch_daily_insights
            result = fetch_daily_insights(token, account_id, target_date)

        elif platform == "ga4":
            if not access_token:
                raise ValueError("GA4: Service Account JSON não configurado.")
            from app.integrations.ga4 import fetch_daily_insights
            result = fetch_daily_insights(access_token, account_id, target_date)

        else:
            logger.warning("Unknown platform: %s", platform)
            return {"client_id": client_id, "platform": platform, "status": "unknown_platform"}

        # Upsert MetricSnapshot for this client + date
        _upsert_metric_snapshot(db, client_id, platform, target_date, result)

        # Log success
        _log_sync(db, client_id, platform, "success", str(result))

        # Update integration last_sync_at
        from datetime import datetime, timezone
        integration.last_sync_at = datetime.now(timezone.utc)
        integration.sync_status = "success"
        db.commit()

        logger.info(
            "Sync completed for client_id=%s platform=%s result=%s",
            client_id,
            platform,
            result,
        )
        return {"client_id": client_id, "platform": platform, "status": "success", "data": result}

    except Exception as e:
        logger.error(
            "Sync FAILED for client_id=%s platform=%s error=%s",
            client_id,
            platform,
            str(e),
        )
        try:
            _log_sync(db, client_id, platform, "failed", str(e))
            if integration:
                integration.sync_status = "failed"
            db.commit()
        except Exception:
            db.rollback()

        return {"client_id": client_id, "platform": platform, "status": "failed", "error": str(e)}

    finally:
        db.close()


def _upsert_metric_snapshot(
    db: Session,
    client_id: int,
    platform: str,
    target_date: date,
    data: dict,
):
    """Upsert MetricSnapshot keyed by (client_id, week_start, source)."""
    week_start = target_date - timedelta(days=target_date.weekday())

    existing = db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.client_id == client_id,
            MetricSnapshot.week_start == week_start,
            MetricSnapshot.source == platform,
        )
    ).scalars().first()

    if existing:
        snapshot = existing
    else:
        snapshot = MetricSnapshot(
            client_id=client_id,
            week_start=week_start,
            source=platform,
        )
        db.add(snapshot)

    if platform in ("meta", "google"):
        snapshot.ad_spend = (float(snapshot.ad_spend or 0)) + data.get("spend", 0)
        snapshot.impressions = (snapshot.impressions or 0) + data.get("impressions", 0)
        snapshot.clicks = (snapshot.clicks or 0) + data.get("clicks", 0)
        if data.get("cpc"):
            snapshot.cpc = data["cpc"]
        if data.get("ctr"):
            snapshot.ctr = data["ctr"]
        if platform == "meta":
            snapshot.conversions = (snapshot.conversions or 0) + data.get("leads", 0)
        elif platform == "google":
            snapshot.conversions = (snapshot.conversions or 0) + int(data.get("conversions", 0))

    elif platform == "ga4":
        lp = data.get("lp_sessions") or data.get("sessions", 0)
        if lp:
            snapshot.lp_sessions = (snapshot.lp_sessions or 0) + lp
        ga4_conv = data.get("conversions", 0)
        if ga4_conv and not snapshot.conversions:
            snapshot.conversions = ga4_conv

    db.flush()


def _log_sync(db: Session, client_id: int, platform: str, status: str, details: str):
    """Log a sync attempt to the sync_logs table."""
    try:
        log = SyncLog(
            client_id=client_id,
            platform=platform,
            status=status,
            error_message=details[:1000] if status == "failed" else None,
        )
        db.add(log)
        db.flush()
    except Exception as e:
        logger.warning("Failed to log sync: %s", str(e))


@celery_app.task(name="app.tasks.sync_ads.sync_all_clients")
def sync_all_clients():
    """Enqueue individual sync tasks for every active client integration.

    Called by Celery Beat every 6 hours.
    """
    logger.info("Starting sync_all_clients sweep...")

    db = _get_sync_db_session()

    try:
        integrations = db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.is_active == True,
                IntegrationSetting.platform.in_(["meta", "google", "ga4"]),
            )
        ).scalars().all()

        enqueued = 0
        for integration in integrations:
            # Only sync if there's a token configured
            if integration.encrypted_access_token or integration.encrypted_refresh_token:
                sync_client_ads.delay(integration.client_id, integration.platform)
                enqueued += 1

        logger.info(
            "sync_all_clients sweep completed. Enqueued %d sync tasks.",
            enqueued,
        )
        return {"status": "ok", "enqueued": enqueued}

    except Exception as e:
        logger.error("sync_all_clients failed: %s", str(e))
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()
