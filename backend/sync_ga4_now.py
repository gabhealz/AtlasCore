"""Sincroniza sessões do site (GA4) por cliente/semana via Service Account.

Lê a credencial de settings.GA4_SERVICE_ACCOUNT_B64 (base64 do JSON, no .env) e,
para cada cliente com ga4_property_id, busca as sessões da semana e faz upsert em
metric_snapshots (source='ga4', campo lp_sessions). Uso: python sync_ga4_now.py [semanas_backfill]
"""
import asyncio
import base64
import json
import logging
import sys
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import base as _base  # noqa: F401
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.client import Client
from app.models.metric_snapshot import MetricSnapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sa_json() -> str | None:
    if not settings.GA4_SERVICE_ACCOUNT_B64:
        return None
    return base64.b64decode(settings.GA4_SERVICE_ACCOUNT_B64).decode("utf-8")


def fetch_sessions(sa_json: str, property_id: str, since: str, until: str) -> dict | None:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest
    from google.oauth2 import service_account as sa

    sa_info = json.loads(sa_json)
    creds = sa.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=since, end_date=until)],
        metrics=[Metric(name="sessions"), Metric(name="conversions"), Metric(name="newUsers")],
    )
    resp = client.run_report(req)
    if not resp.rows:
        return {"sessions": 0, "conversions": 0, "new_users": 0}
    row = resp.rows[0]
    return {
        "sessions": int(float(row.metric_values[0].value)),
        "conversions": int(float(row.metric_values[1].value)),
        "new_users": int(float(row.metric_values[2].value)),
    }


async def main() -> None:
    sa_json = _sa_json()
    if not sa_json:
        logger.error("GA4_SERVICE_ACCOUNT_B64 não configurado no .env.")
        return
    backfill = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    weeks = [current_monday - timedelta(days=7 * n) for n in range(backfill + 1)]

    async with AsyncSessionLocal() as db:
        clients = (await db.execute(
            select(Client).where(Client.ga4_property_id.isnot(None))
        )).scalars().all()
        synced = 0
        for c in clients:
            for monday in weeks:
                until = min(monday + timedelta(days=6), today)
                try:
                    data = await asyncio.to_thread(
                        fetch_sessions, sa_json, c.ga4_property_id, monday.isoformat(), until.isoformat()
                    )
                except Exception as exc:
                    logger.warning("GA4 erro %s (%s): %s", c.name, monday, str(exc)[:160])
                    continue
                if not data or data["sessions"] == 0:
                    continue
                stmt = pg_insert(MetricSnapshot).values(
                    client_id=c.id, week_start=monday, date=monday, source="ga4",
                    lp_sessions=data["sessions"],
                ).on_conflict_do_update(
                    index_elements=["client_id", "week_start", "source"],
                    set_={"lp_sessions": data["sessions"]},
                )
                await db.execute(stmt)
                synced += 1
                logger.info("%s [%s]: %s sessões | %s conv | %s novos",
                            c.name, monday, data["sessions"], data["conversions"], data["new_users"])
        await db.commit()
        logger.info("GA4 snapshots sincronizados=%s | semanas=%s", synced, len(weeks))


if __name__ == "__main__":
    asyncio.run(main())
