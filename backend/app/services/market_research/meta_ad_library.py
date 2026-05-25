"""Cliente da Meta Ad Library API (anuncios ativos de concorrentes).

Doc: https://www.facebook.com/ads/library/api/  (endpoint graph ads_archive).
Usa o token GLOBAL da agencia (settings.META_AD_LIBRARY_TOKEN). Gratuito, mas
exige um app Meta e um token de acesso valido.

LIMITACAO VERIFICADA (mai/2026, doc oficial do ads_archive): para anuncios que
NAO atingem a Uniao Europeia, a API so retorna anuncios sobre "questoes sociais,
eleicoes ou politica". Anuncios COMERCIAIS no Brasil (clinicas, medicos) NAO sao
retornados por este endpoint. Ou seja: para o caso de uso Healz (concorrentes de
clinicas no BR), esta fonte tende a vir VAZIA. Os anuncios comerciais BR existem
no site da Ad Library, mas so via navegacao manual, nao pela API. Mantido aqui
para cenarios EU/politicos ou caso a Meta mude a politica.

Nunca levanta excecao: em qualquer erro retorna lista vazia + uma nota.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.market_research.base import MetaAd

logger = logging.getLogger(__name__)

_GRAPH_URL = "https://graph.facebook.com/v21.0/ads_archive"
_FIELDS = (
    "id,page_name,ad_creative_bodies,ad_creative_link_titles,"
    "ad_delivery_start_time,ad_snapshot_url,publisher_platforms"
)


def _first(value: object) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str):
        return value
    return ""


async def fetch_meta_ads(
    search_terms: str,
    *,
    limit: int,
) -> tuple[list[MetaAd], list[str]]:
    if not settings.meta_ad_library_enabled:
        return [], []

    if not search_terms.strip():
        return [], ["Meta Ad Library: sem termo de busca derivado do briefing."]

    country = settings.META_AD_LIBRARY_COUNTRY.strip().upper() or "BR"
    params = {
        "access_token": settings.META_AD_LIBRARY_TOKEN,
        "search_terms": search_terms,
        "ad_reached_countries": f'["{country}"]',
        "ad_active_status": "ACTIVE",
        "fields": _FIELDS,
        "limit": str(max(1, min(limit, 50))),
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.MARKET_DATA_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(_GRAPH_URL, params=params)
    except httpx.HTTPError as exc:
        logger.warning("Meta Ad Library request failed: %s", exc)
        return [], [f"Meta Ad Library indisponivel (erro de conexao): {exc}"]

    if response.status_code != 200:
        detail = _extract_error(response)
        logger.warning("Meta Ad Library returned %s: %s", response.status_code, detail)
        return [], [f"Meta Ad Library retornou erro {response.status_code}: {detail}"]

    try:
        payload = response.json()
    except ValueError:
        return [], ["Meta Ad Library retornou resposta nao-JSON."]

    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        return [], [f"Meta Ad Library: nenhum anuncio ativo para '{search_terms}'."]

    ads: list[MetaAd] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        platforms = row.get("publisher_platforms")
        ads.append(
            MetaAd(
                page_name=str(row.get("page_name", "")) or "Pagina nao informada",
                body=_first(row.get("ad_creative_bodies")),
                cta_title=_first(row.get("ad_creative_link_titles")),
                platforms=", ".join(platforms)
                if isinstance(platforms, list)
                else str(platforms or ""),
                started_at=str(row.get("ad_delivery_start_time", "")),
                snapshot_url=str(row.get("ad_snapshot_url", "")),
            )
        )

    return ads, []


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                return str(error.get("message", "erro desconhecido"))
    except ValueError:
        pass
    return response.text[:200]
