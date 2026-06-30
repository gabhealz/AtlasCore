"""Orquestra a coleta de dados de mercado a partir das fontes disponiveis.

Regras:
- Roda Meta Ad Library e a fonte de volume/CPC em paralelo.
- Para volume/CPC, prefere Google Ads Keyword Planner (gratuito) quando
  configurado; senao usa DataForSEO.
- Nunca levanta excecao: consolida tudo em CollectedMarketData, registrando
  notas para fontes ausentes ou com erro.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.market_research import (
    apify,
    dataforseo,
    google_keywords,
    meta_ad_library,
)
from app.services.market_research.base import CollectedMarketData

logger = logging.getLogger(__name__)


async def collect_market_data(
    *,
    specialty: str | None,
    keywords: list[str],
    meta_search_terms: str | None = None,
    city: str | None = None,
) -> CollectedMarketData:
    data = CollectedMarketData()

    any_source_configured = (
        settings.meta_ad_library_enabled
        or settings.dataforseo_enabled
        or settings.google_ads_keywords_enabled
        or settings.apify_enabled
    )
    if not any_source_configured:
        # Nenhuma credencial: nao injeta nada, pipeline segue so com web_search.
        return data

    max_items = max(1, settings.MARKET_DATA_MAX_ITEMS)
    meta_terms = (meta_search_terms or specialty or "").strip()

    meta_task = meta_ad_library.fetch_meta_ads(meta_terms, limit=max_items)
    keyword_task = _collect_keywords(keywords, limit=max_items)
    competitors_task = apify.fetch_competitors(
        specialty=specialty,
        city=city,
        limit=settings.APIFY_MAPS_MAX_PLACES,
    )

    results = await asyncio.gather(
        meta_task, keyword_task, competitors_task, return_exceptions=True
    )

    meta_result, keyword_result, competitors_result = results

    if isinstance(meta_result, BaseException):
        logger.warning("Meta collection raised: %s", meta_result)
        data.notes.append(f"Meta Ad Library falhou inesperadamente: {meta_result}")
    else:
        ads, notes = meta_result
        data.meta_ads.extend(ads)
        data.notes.extend(notes)
        if ads:
            data.sources_used.append("Meta Ad Library")

    if isinstance(competitors_result, BaseException):
        logger.warning("Apify collection raised: %s", competitors_result)
        data.notes.append(
            f"Apify Google Maps falhou inesperadamente: {competitors_result}"
        )
    else:
        competitors, notes = competitors_result
        data.competitors.extend(competitors)
        data.notes.extend(notes)
        if competitors:
            data.sources_used.append("Google Maps (Apify)")

    if isinstance(keyword_result, BaseException):
        logger.warning("Keyword collection raised: %s", keyword_result)
        data.notes.append(f"Coleta de keywords falhou: {keyword_result}")
    else:
        metrics, notes, source_label = keyword_result
        data.keywords.extend(metrics)
        data.notes.extend(notes)
        if metrics and source_label:
            data.sources_used.append(source_label)

    return data


async def _collect_keywords(keywords: list[str], *, limit: int):
    """Escolhe a fonte de volume/CPC e retorna (metrics, notes, source_label)."""
    if settings.google_ads_keywords_enabled:
        metrics, notes = await google_keywords.fetch_keyword_metrics(
            keywords, limit=limit
        )
        if settings.dataforseo_enabled:
            notes.append(
                "DataForSEO tambem esta configurado, mas usamos Google Ads "
                "Keyword Planner (gratuito) como fonte primaria de volume/CPC."
            )
        return metrics, notes, "Google Ads Keyword Planner"

    if settings.dataforseo_enabled:
        metrics, notes = await dataforseo.fetch_keyword_metrics(keywords, limit=limit)
        return metrics, notes, "DataForSEO"

    return [], [], None
