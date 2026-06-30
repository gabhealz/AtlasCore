"""Cliente Apify: coleta concorrentes via Google Maps (Rota A do benchmark).

Roda um actor de Google Maps de forma SÍNCRONA (run-sync-get-dataset-items) e
mapeia cada "place" para um Competitor. Com o enriquecimento de contatos ligado
(scrapeContacts), o actor extrai do site de cada lugar os links de Instagram e
Facebook — o que resolve o "@" do concorrente sem precisar saber de antemão —
além da nota e do número de avaliações do Google.

Usa o token GLOBAL da agência (settings.APIFY_TOKEN, free tier $5/mês). O parser
é defensivo de propósito: actors diferentes nomeiam os campos de formas distintas
(totalScore/rating, reviewsCount/userRatingCount, instagrams/instagramUrl, ...),
então tentamos várias chaves para cada dado.

Nunca levanta exceção: em qualquer erro retorna lista vazia + uma nota.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.market_research.base import Competitor

logger = logging.getLogger(__name__)

_BASE = "https://api.apify.com/v2/acts"

# Chaves candidatas por campo (ordem = prioridade). Mantém o parser tolerante a
# variações de schema entre actors de Google Maps no Apify Store.
_NAME_KEYS = ("title", "name", "placeName", "businessName")
_RATING_KEYS = ("totalScore", "rating", "stars", "score", "averageRating")
_REVIEWS_KEYS = (
    "reviewsCount",
    "reviewCount",
    "userRatingCount",
    "reviewsCountText",
    "numberOfReviews",
)
_CATEGORY_KEYS = ("categoryName", "category", "type")
_WEBSITE_KEYS = ("website", "websiteUrl", "url", "domain")
_ADDRESS_KEYS = ("address", "fullAddress", "street", "addressString")
_FOLLOWERS_KEYS = (
    "instagramFollowers",
    "followersCount",
    "followers",
    "igFollowers",
)


def _actor_path(actor: str) -> str:
    """compass/crawler-google-places -> compass~crawler-google-places."""
    return actor.strip().replace("/", "~")


async def fetch_competitors(
    *,
    specialty: str | None,
    city: str | None,
    limit: int,
) -> tuple[list[Competitor], list[str]]:
    if not settings.apify_enabled:
        return [], []

    spec = (specialty or "").strip()
    if not spec:
        return [], [
            "Apify Google Maps: especialidade nao definida; "
            "busca de concorrentes pulada."
        ]

    local = (city or "").strip()
    query = f"{spec} {local}".strip() if local else spec

    actor = _actor_path(settings.APIFY_GOOGLE_MAPS_ACTOR)
    url = f"{_BASE}/{actor}/run-sync-get-dataset-items"
    max_places = max(1, min(limit, 20))
    body = {
        "searchStringsArray": [query],
        "maxCrawledPlacesPerSearch": max_places,
        "language": settings.APIFY_MAPS_LANGUAGE,
        "countryCode": settings.APIFY_MAPS_COUNTRY,
        # Enriquecimento: extrai e-mail/redes sociais do site do lugar.
        "scrapeContacts": True,
        "skipClosedPlaces": True,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.APIFY_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                url,
                params={"token": settings.APIFY_TOKEN},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Apify request failed: %s", exc)
        return [], [f"Apify Google Maps indisponivel (erro de conexao): {exc}"]

    if response.status_code not in (200, 201):
        detail = _extract_error(response)
        logger.warning("Apify returned %s: %s", response.status_code, detail)
        return [], [
            f"Apify Google Maps retornou erro HTTP {response.status_code}: {detail}"
        ]

    try:
        items = response.json()
    except ValueError:
        return [], ["Apify Google Maps retornou resposta nao-JSON."]

    if not isinstance(items, list) or not items:
        return [], [
            f"Apify Google Maps: nenhum concorrente encontrado para '{query}'."
        ]

    competitors: list[Competitor] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        comp = _parse_place(item)
        if comp is not None:
            competitors.append(comp)

    if not competitors:
        return [], [
            f"Apify Google Maps: resultados sem dados utilizaveis para '{query}'."
        ]

    return competitors, []


def _parse_place(item: dict[str, Any]) -> Competitor | None:
    name = _first_str(item, _NAME_KEYS)
    if not name:
        return None
    return Competitor(
        name=name,
        rating=_as_float(_first_val(item, _RATING_KEYS)),
        reviews_count=_as_int(_first_val(item, _REVIEWS_KEYS)),
        category=_first_str(item, _CATEGORY_KEYS),
        website=_first_str(item, _WEBSITE_KEYS),
        instagram_url=_first_social(item, "instagram"),
        instagram_followers=_as_int(_first_val(item, _FOLLOWERS_KEYS)),
        facebook_url=_first_social(item, "facebook"),
        address=_first_str(item, _ADDRESS_KEYS),
    )


def _first_val(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, "", []):
            return item[key]
    return None


def _first_str(item: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _first_val(item, keys)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_social(item: dict[str, Any], platform: str) -> str | None:
    """Procura o link da rede social em vários formatos de schema:
    lista `instagrams`/`facebooks`, string `instagramUrl`/`instagram`, ou
    dentro de um dict `socialMedia`/`socialProfiles`/`contactDetails`."""
    plural = f"{platform}s"
    value = item.get(plural)
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str) and platform in entry.lower():
                return entry.strip()

    for key in (f"{platform}Url", f"{platform}URL", platform):
        candidate = item.get(key)
        if isinstance(candidate, str) and platform in candidate.lower():
            return candidate.strip()

    for container_key in ("socialMedia", "socialProfiles", "contactDetails"):
        container = item.get(container_key)
        if isinstance(container, dict):
            found = _first_social(container, platform)
            if found:
                return found
        if isinstance(container, list):
            for entry in container:
                if isinstance(entry, str) and platform in entry.lower():
                    return entry.strip()

    return None


def _extract_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                return str(error.get("message", "erro desconhecido"))
            if isinstance(error, str):
                return error
    except ValueError:
        pass
    return response.text[:200]


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        # "1,234" / "1.234 avaliações" / "2 mil" -> melhor esforço numérico.
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                return None
    return None


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            return float(value.replace(",", ".").strip())
        return float(value)
    except (TypeError, ValueError):
        return None
