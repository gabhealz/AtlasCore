"""Cliente DataForSEO (volume de busca + CPC reais por palavra-chave).

Doc: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/live/
Endpoint pago, autenticacao HTTP Basic (login/senha da conta DataForSEO).

Nunca levanta excecao: em qualquer erro retorna lista vazia + uma nota.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.market_research.base import KeywordMetric

logger = logging.getLogger(__name__)

_URL = (
    "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
)


async def fetch_keyword_metrics(
    keywords: list[str],
    *,
    limit: int,
) -> tuple[list[KeywordMetric], list[str]]:
    if not settings.dataforseo_enabled:
        return [], []

    cleaned = [kw.strip() for kw in keywords if kw and kw.strip()][: max(1, limit)]
    if not cleaned:
        return [], ["DataForSEO: nenhuma palavra-chave derivada do briefing."]

    body = [
        {
            "keywords": cleaned,
            "location_code": settings.DATAFORSEO_LOCATION_CODE,
            "language_code": settings.DATAFORSEO_LANGUAGE_CODE,
        }
    ]

    try:
        async with httpx.AsyncClient(
            timeout=settings.MARKET_DATA_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                _URL,
                json=body,
                auth=(settings.DATAFORSEO_LOGIN, settings.DATAFORSEO_PASSWORD),
            )
    except httpx.HTTPError as exc:
        logger.warning("DataForSEO request failed: %s", exc)
        return [], [f"DataForSEO indisponivel (erro de conexao): {exc}"]

    if response.status_code != 200:
        logger.warning("DataForSEO returned %s", response.status_code)
        return [], [f"DataForSEO retornou erro HTTP {response.status_code}."]

    try:
        payload = response.json()
    except ValueError:
        return [], ["DataForSEO retornou resposta nao-JSON."]

    items = _extract_result_items(payload)
    if not items:
        return [], ["DataForSEO: nenhum dado retornado para as palavras-chave."]

    location = f"location_code {settings.DATAFORSEO_LOCATION_CODE}"
    metrics: list[KeywordMetric] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = item.get("keyword")
        if not isinstance(keyword, str):
            continue
        metrics.append(
            KeywordMetric(
                keyword=keyword,
                avg_monthly_searches=_as_int(item.get("search_volume")),
                cpc=_as_float(item.get("cpc")),
                competition=_competition_text(item),
                source="DataForSEO (Google Ads)",
                location=location,
            )
        )

    return metrics, []


def _extract_result_items(payload: object) -> list:
    if not isinstance(payload, dict):
        return []
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return []
    items: list = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        result = task.get("result")
        if isinstance(result, list):
            items.extend(result)
    return items


def _competition_text(item: dict) -> str | None:
    level = item.get("competition_level") or item.get("competition")
    if level is None:
        return None
    return str(level)


def _as_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
