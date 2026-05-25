"""Background tasks for syncing ad platform data.

These are the REAL implementations that connect to Meta Ads, Google Ads,
and GA4 APIs using per-client encrypted credentials.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_value
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
    """Create or update MetricSnapshot with data from the given platform."""
    # Try to find existing snapshot for this client + date
    existing = db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.client_id == client_id,
            MetricSnapshot.date == target_date,
        )
    ).scalars().first()

    if existing:
        snapshot = existing
    else:
        # Calculate week_start
        week_start = target_date - timedelta(days=target_date.weekday())
        snapshot = MetricSnapshot(
            client_id=client_id,
            date=target_date,
            week_start=week_start,
            ad_spend=0,
            leads=0,
            appointments=0,
            revenue=0,
            consultations=0,
        )
        db.add(snapshot)

    # Update fields based on platform
    if platform in ("meta", "google"):
        # Accumulate spend from both platforms
        current_spend = float(snapshot.ad_spend or 0)
        current_spend += data.get("spend", 0)
        snapshot.ad_spend = current_spend

        # Accumulate leads/conversions
        current_leads = int(snapshot.leads or 0)
        if platform == "meta":
            current_leads += data.get("leads", 0)
        elif platform == "google":
            current_leads += int(data.get("conversions", 0))
        snapshot.leads = current_leads

    elif platform == "ga4":
        # GA4 conversions can supplement leads if no Tintim
        ga4_conversions = data.get("conversions", 0)
        if ga4_conversions > 0:
            # Only update if current leads is 0 (Tintim takes priority)
            if not snapshot.leads:
                snapshot.leads = ga4_conversions

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
