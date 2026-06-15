"""Vincula contas de anúncio da Meta aos clientes e sincroniza a semana atual.

Usa o token compartilhado (settings.META_ACCESS_TOKEN) + o meta_account_id de cada
cliente. Lê insights agregados da semana (Graph API) e faz upsert em metric_snapshots
(source='meta'). Pode rodar quantas vezes quiser (idempotente).
"""
import asyncio
import json
import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import base as _base  # noqa: F401
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.client import Client
from app.models.metric_snapshot import MetricSnapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"

# account_id da Meta -> trecho do nome do cliente (ILIKE). Apenas matches confiáveis.
MAPPING = {
    "591781719101098": "PEROLA NEGRA",
    "1944748722571111": "CONEPEN",
    "808579971322032": "SKINDOO",
    "652347303996752": "UROCENTER",
    "4006937759560574": "SCOPACASA",
    "1259232005864334": "ISABEL TOSTES",
    "1331904948631196": "EJJEMED",
    "1474652417562399": "FABRICIO",
    "1833310940891327": "RENATO DA SILVA FARIA",
}

LEAD_ACTIONS = ("lead", "offsite_conversion.fb_pixel_lead", "onsite_conversion.lead_grouped")


async def link_accounts(db) -> int:
    linked = 0
    for acc, kw in MAPPING.items():
        rows = (await db.execute(select(Client).where(Client.name.ilike(f"%{kw}%")))).scalars().all()
        for c in rows:
            c.meta_account_id = acc
            linked += 1
    await db.commit()
    return linked


async def fetch_week(token: str, account_id: str, since: str, until: str) -> dict | None:
    url = f"{GRAPH}/act_{account_id}/insights"
    params = {
        "fields": "spend,impressions,clicks,cpc,ctr,actions",
        "level": "account",
        "time_range": json.dumps({"since": since, "until": until}),
        "access_token": token,
    }
    async with httpx.AsyncClient(timeout=40) as cli:
        r = await cli.get(url, params=params)
        if r.status_code != 200:
            logger.warning("Meta %s HTTP %s: %s", account_id, r.status_code, r.text[:200])
            return None
        d = r.json()
    data = d.get("data", [])
    if not data:
        return None
    row = data[0]
    leads = 0
    for a in row.get("actions", []):
        if a.get("action_type") in LEAD_ACTIONS:
            leads += int(float(a.get("value", 0)))
    return {
        "spend": float(row.get("spend", 0) or 0),
        "impressions": int(row.get("impressions", 0) or 0),
        "clicks": int(row.get("clicks", 0) or 0),
        "cpc": float(row.get("cpc", 0) or 0),
        "ctr": float(row.get("ctr", 0) or 0),
        "leads": leads,
    }


async def main() -> None:
    token = settings.META_ACCESS_TOKEN
    if not token:
        logger.error("META_ACCESS_TOKEN não configurado.")
        return
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    async with AsyncSessionLocal() as db:
        linked = await link_accounts(db)
        clients = (await db.execute(
            select(Client).where(Client.meta_account_id.isnot(None))
        )).scalars().all()
        synced = 0
        for c in clients:
            try:
                ins = await fetch_week(token, c.meta_account_id, monday.isoformat(), today.isoformat())
            except Exception as exc:
                logger.warning("Erro %s: %s", c.name, exc)
                continue
            if not ins:
                logger.info("Sem dados Meta: %s", c.name)
                continue
            stmt = pg_insert(MetricSnapshot).values(
                client_id=c.id, week_start=monday, date=monday, source="meta",
                impressions=ins["impressions"], clicks=ins["clicks"], ctr=ins["ctr"],
                cpc=ins["cpc"], ad_spend=ins["spend"], conversions=ins["leads"],
            ).on_conflict_do_update(
                index_elements=["client_id", "week_start", "source"],
                set_={
                    "impressions": ins["impressions"], "clicks": ins["clicks"],
                    "ctr": ins["ctr"], "cpc": ins["cpc"], "ad_spend": ins["spend"],
                    "conversions": ins["leads"],
                },
            )
            await db.execute(stmt)
            synced += 1
            logger.info("%s: R$%.2f | %s imp | %s cliques | %s leads",
                        c.name, ins["spend"], ins["impressions"], ins["clicks"], ins["leads"])
        await db.commit()
        logger.info("Vinculados=%s | Sincronizados=%s", linked, synced)


if __name__ == "__main__":
    asyncio.run(main())
