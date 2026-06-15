"""Sincroniza insights do Google Ads por cliente/semana via MCC (token compartilhado).

Usa o refresh token da MCC (settings.GOOGLE_ADS_REFRESH_TOKEN) + developer token +
login_customer_id (MCC). Para cada cliente com google_account_id, busca métricas da
semana (cost, impressões, cliques, conversões) e faz upsert em metric_snapshots
(source='google'). Idempotente. Uso: python sync_google_ads_now.py [semanas_backfill]
"""
import asyncio
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


def _build_client():
    from google.ads.googleads.client import GoogleAdsClient

    creds = {
        "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_ADS_CLIENT_ID,
        "client_secret": settings.GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": settings.GOOGLE_ADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    # Acesso é direto em cada conta de cliente (leitor por conta), NÃO via MCC.
    # Por isso NÃO definimos login_customer_id — cada customer_id é consultado direto.
    # (Se um dia o acesso passar a ser via MCC, definir GOOGLE_ADS_USE_MCC=1.)
    if (getattr(settings, "GOOGLE_ADS_USE_MCC", "") or "") in ("1", "true", "True"):
        mcc = (settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID or "").replace("-", "").replace(" ", "")
        if mcc:
            creds["login_customer_id"] = mcc
    return GoogleAdsClient.load_from_dict(creds)


def fetch_week(ga_client, customer_id: str, since: str, until: str) -> dict | None:
    """Soma métricas diárias do período (uma linha por dia)."""
    customer_id = customer_id.replace("-", "").replace(" ", "")
    service = ga_client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions
        FROM customer
        WHERE segments.date >= '{since}' AND segments.date <= '{until}'
    """
    spend = impressions = clicks = 0.0
    conversions = 0.0
    rows = 0
    for row in service.search(customer_id=customer_id, query=query):
        m = row.metrics
        spend += m.cost_micros / 1_000_000
        impressions += m.impressions
        clicks += m.clicks
        conversions += m.conversions
        rows += 1
    if rows == 0:
        return None
    impressions = int(impressions)
    clicks = int(clicks)
    ctr = (clicks / impressions * 100) if impressions else 0.0
    cpc = (spend / clicks) if clicks else 0.0
    return {
        "spend": round(spend, 2),
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "conversions": round(conversions, 2),
    }


async def main() -> None:
    if not settings.GOOGLE_ADS_REFRESH_TOKEN:
        logger.error("GOOGLE_ADS_REFRESH_TOKEN não configurado.")
        return

    backfill = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    weeks = [current_monday - timedelta(days=7 * n) for n in range(backfill + 1)]

    ga_client = _build_client()

    async with AsyncSessionLocal() as db:
        clients = (await db.execute(
            select(Client).where(Client.google_account_id.isnot(None))
        )).scalars().all()
        synced = 0
        for c in clients:
            for monday in weeks:
                until = min(monday + timedelta(days=6), today)
                try:
                    ins = fetch_week(ga_client, c.google_account_id, monday.isoformat(), until.isoformat())
                except Exception as exc:
                    logger.warning("Erro %s (%s): %s", c.name, monday, str(exc)[:200])
                    continue
                if not ins:
                    continue
                stmt = pg_insert(MetricSnapshot).values(
                    client_id=c.id, week_start=monday, date=monday, source="google",
                    impressions=ins["impressions"], clicks=ins["clicks"], ctr=ins["ctr"],
                    cpc=ins["cpc"], ad_spend=ins["spend"], conversions=ins["conversions"],
                ).on_conflict_do_update(
                    index_elements=["client_id", "week_start", "source"],
                    set_={
                        "impressions": ins["impressions"], "clicks": ins["clicks"],
                        "ctr": ins["ctr"], "cpc": ins["cpc"], "ad_spend": ins["spend"],
                        "conversions": ins["conversions"],
                    },
                )
                await db.execute(stmt)
                synced += 1
                logger.info("%s [%s]: R$%.2f | %s imp | %s cliques | %s conv",
                            c.name, monday, ins["spend"], ins["impressions"], ins["clicks"], ins["conversions"])
        await db.commit()
        logger.info("Snapshots Google Ads sincronizados=%s | semanas=%s", synced, len(weeks))


if __name__ == "__main__":
    asyncio.run(main())
