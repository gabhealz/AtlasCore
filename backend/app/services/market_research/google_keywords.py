"""Cliente Google Ads Keyword Planner (volume + CPC reais, alternativa gratuita).

Usa a biblioteca oficial `google-ads` com credenciais GLOBAIS da agencia
(developer token + OAuth2 refresh token). A API e sincrona e pesada, por isso a
chamada roda em thread separada (asyncio.to_thread) e o import e lazy.

Nunca levanta excecao: em qualquer erro retorna lista vazia + uma nota.

Setup necessario (mais trabalhoso que DataForSEO):
- Conta Google Ads + developer token aprovado.
- OAuth2: client_id, client_secret e refresh_token.
- customer_id (e login_customer_id se usar MCC).
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.market_research.base import KeywordMetric

logger = logging.getLogger(__name__)

# Constantes de segmentacao: pt-BR e Brasil.
_LANGUAGE_PT = "languageConstants/1014"
_GEO_BRAZIL = "geoTargetConstants/2076"


async def fetch_keyword_metrics(
    keywords: list[str],
    *,
    limit: int,
) -> tuple[list[KeywordMetric], list[str]]:
    if not settings.google_ads_keywords_enabled:
        return [], []

    cleaned = [kw.strip() for kw in keywords if kw and kw.strip()][: max(1, limit)]
    if not cleaned:
        return [], ["Google Ads Keyword Planner: sem palavras-chave do briefing."]

    try:
        return await asyncio.to_thread(_generate, cleaned)
    except Exception as exc:  # noqa: BLE001 - degradacao segura por design
        logger.warning("Google Ads Keyword Planner failed: %s", exc)
        return [], [f"Google Ads Keyword Planner indisponivel: {exc}"]


def _build_config() -> dict:
    config = {
        "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_ADS_CLIENT_ID,
        "client_secret": settings.GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": settings.GOOGLE_ADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    login_customer_id = settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID.strip().replace("-", "")
    if login_customer_id:
        config["login_customer_id"] = login_customer_id
    return config


def _generate(keywords: list[str]) -> tuple[list[KeywordMetric], list[str]]:
    from google.ads.googleads.client import GoogleAdsClient

    client = GoogleAdsClient.load_from_dict(_build_config())
    customer_id = settings.GOOGLE_ADS_CUSTOMER_ID.strip().replace("-", "")
    idea_service = client.get_service("KeywordPlanIdeaService")

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = _LANGUAGE_PT
    request.geo_target_constants.append(_GEO_BRAZIL)
    request.include_adult_keywords = False
    request.keyword_seed.keywords.extend(keywords)

    response = idea_service.generate_keyword_ideas(request=request)

    metrics: list[KeywordMetric] = []
    for idea in response:
        idea_metrics = getattr(idea, "keyword_idea_metrics", None)
        avg_searches = (
            getattr(idea_metrics, "avg_monthly_searches", None)
            if idea_metrics
            else None
        )
        cpc = _bid_to_cpc(idea_metrics)
        competition = (
            getattr(getattr(idea_metrics, "competition", None), "name", None)
            if idea_metrics
            else None
        )
        metrics.append(
            KeywordMetric(
                keyword=getattr(idea, "text", ""),
                avg_monthly_searches=avg_searches,
                cpc=cpc,
                competition=competition,
                source="Google Ads Keyword Planner",
                location="Brasil (geoTargetConstants/2076)",
            )
        )

    if not metrics:
        return [], ["Google Ads Keyword Planner: nenhuma ideia retornada."]
    return metrics, []


def _bid_to_cpc(idea_metrics: object) -> float | None:
    """Usa o lance de topo de pagina (alto) em micros como proxy de CPC."""
    if idea_metrics is None:
        return None
    micros = getattr(idea_metrics, "high_top_of_page_bid_micros", None)
    if not micros:
        micros = getattr(idea_metrics, "low_top_of_page_bid_micros", None)
    if not micros:
        return None
    try:
        return round(int(micros) / 1_000_000, 2)
    except (TypeError, ValueError):
        return None
