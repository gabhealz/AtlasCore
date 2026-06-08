"""Pesquisa de keywords SEO combinando DataForSEO + base interna da Healz.

Politica:
- Reaproveita do cache (banco) toda keyword consultada ha menos de
  SEO_CACHE_TTL_DAYS; so chama a API paga do DataForSEO para o que falta.
- Mescla com nossa propria base: se ja atendemos clientes/onboardings da
  especialidade pesquisada, devolve esses matches internos.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.client import Client
from app.models.onboarding import Onboarding
from app.models.seo_keyword_cache import SeoKeywordCache
from app.services.market_research import dataforseo


def _normalize(term: str) -> str:
    return " ".join((term or "").lower().split())


async def _internal_matches(db: AsyncSession, specialty: str | None) -> dict:
    cleaned = (specialty or "").strip()
    if not cleaned:
        return {"specialty": None, "clients": [], "onboardings": []}

    like = f"%{cleaned}%"
    clients = (
        (await db.execute(select(Client).where(Client.specialty.ilike(like))))
        .scalars()
        .all()
    )
    onboardings = (
        (await db.execute(select(Onboarding).where(Onboarding.specialty.ilike(like))))
        .scalars()
        .all()
    )
    return {
        "specialty": cleaned,
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "specialty": c.specialty,
                "city": c.city,
                "state": c.state,
                "is_active": bool(c.is_active),
            }
            for c in clients
        ],
        "onboardings": [
            {
                "id": o.id,
                "doctor_name": o.doctor_name,
                "specialty": o.specialty,
                "status": o.status,
            }
            for o in onboardings
        ],
    }


async def search_keywords(
    db: AsyncSession,
    *,
    terms: list[str],
    specialty: str | None = None,
) -> dict:
    location_code = settings.DATAFORSEO_LOCATION_CODE
    language_code = settings.DATAFORSEO_LANGUAGE_CODE
    notes: list[str] = []

    normalized: list[str] = []
    seen: set[str] = set()
    for term in terms:
        norm = _normalize(term)
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)

    results: dict[str, dict] = {}

    cached: dict[str, SeoKeywordCache] = {}
    if normalized:
        rows = (
            await db.execute(
                select(SeoKeywordCache).where(
                    SeoKeywordCache.keyword.in_(normalized),
                    SeoKeywordCache.location_code == location_code,
                    SeoKeywordCache.language_code == language_code,
                )
            )
        ).scalars().all()
        cached = {row.keyword: row for row in rows}

    ttl_days = max(0, settings.SEO_CACHE_TTL_DAYS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)

    misses: list[str] = []
    for norm in normalized:
        row = cached.get(norm)
        if row is not None and row.queried_at is not None and row.queried_at >= cutoff:
            results[norm] = {
                "keyword": norm,
                "avg_monthly_searches": row.avg_monthly_searches,
                "cpc": float(row.cpc) if row.cpc is not None else None,
                "competition": row.competition,
                "source": row.source,
                "from_cache": True,
                "queried_at": row.queried_at.isoformat(),
            }
        else:
            misses.append(norm)

    if misses and settings.dataforseo_enabled:
        metrics, fetch_notes = await dataforseo.fetch_keyword_metrics(
            misses, limit=len(misses)
        )
        notes.extend(fetch_notes)
        now = datetime.now(timezone.utc)
        for metric in metrics:
            keyword = _normalize(metric.keyword)
            stmt = insert(SeoKeywordCache).values(
                keyword=keyword,
                location_code=location_code,
                language_code=language_code,
                avg_monthly_searches=metric.avg_monthly_searches,
                cpc=metric.cpc,
                competition=metric.competition,
                source=metric.source,
                queried_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["keyword", "location_code", "language_code"],
                set_={
                    "avg_monthly_searches": stmt.excluded.avg_monthly_searches,
                    "cpc": stmt.excluded.cpc,
                    "competition": stmt.excluded.competition,
                    "source": stmt.excluded.source,
                    "queried_at": stmt.excluded.queried_at,
                },
            )
            await db.execute(stmt)
            results[keyword] = {
                "keyword": keyword,
                "avg_monthly_searches": metric.avg_monthly_searches,
                "cpc": metric.cpc,
                "competition": metric.competition,
                "source": metric.source,
                "from_cache": False,
                "queried_at": now.isoformat(),
            }
        await db.commit()
    elif misses and not settings.dataforseo_enabled:
        notes.append(
            "DataForSEO nao esta configurado; exibindo apenas dados em cache "
            "e internos."
        )

    keywords = [results[norm] for norm in normalized if norm in results]
    internal = await _internal_matches(db, specialty)

    return {
        "keywords": keywords,
        "internal": internal,
        "notes": notes,
        "location_code": location_code,
        "language_code": language_code,
    }
