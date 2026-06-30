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

import asyncio
import logging
import unicodedata
from typing import Any

import httpx

from app.core.config import settings
from app.services.market_research.base import Competitor, MetaAd

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
                params={
                    "token": settings.APIFY_TOKEN,
                    # Garante os itens inline no corpo (JSON limpo, sem campos
                    # internos/vazios). Sem isso o sync pode devolver corpo vazio.
                    "format": "json",
                    "clean": "true",
                },
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

    notes: list[str] = []

    # Filtro geografico: o Google Maps as vezes devolve lugares de outras cidades/
    # estados. Mantem apenas os cuja ficha de endereco contem a cidade buscada;
    # se isso esvaziar tudo (formato de endereco atipico), mantem a lista original.
    if local:
        filtered = [c for c in competitors if _address_in_city(c.address, local)]
        dropped = len(competitors) - len(filtered)
        if filtered:
            if dropped:
                notes.append(
                    f"Apify Google Maps: {dropped} concorrente(s) de fora de "
                    f"'{local}' descartado(s) por filtro geografico."
                )
            competitors = filtered
        else:
            notes.append(
                "Apify Google Maps: filtro geografico nao casou nenhum endereco "
                f"com '{local}'; mantendo a lista completa."
            )

    # Enriquecimento em paralelo: (1) seguidores do Instagram a partir dos @
    # resolvidos pelo Maps (Apify), e (2) trecho do site de cada concorrente
    # (fetch direto, gratis) para alimentar copy/posicionamento de forma
    # deterministica. Best-effort, nunca bloqueia.
    async def _ig():
        if not settings.apify_instagram_enabled:
            return 0
        return await _enrich_instagram_followers(competitors)

    ig_res, site_res = await asyncio.gather(
        _ig(), _enrich_site_snippets(competitors), return_exceptions=True
    )
    if isinstance(ig_res, BaseException):
        logger.warning("Apify Instagram enrichment failed: %s", ig_res)
        notes.append(f"Apify Instagram: enriquecimento de seguidores falhou: {ig_res}")
    elif ig_res:
        notes.append(f"Apify Instagram: seguidores coletados de {ig_res} perfil(is).")
    if isinstance(site_res, BaseException):
        logger.warning("Site snippet enrichment failed: %s", site_res)
    elif site_res:
        notes.append(f"Sites dos concorrentes lidos: {site_res}.")

    return competitors, notes


def _norm(text: str | None) -> str:
    """Lowercase + remove acentos para comparacao tolerante."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return no_accents.lower().strip()


def _address_in_city(address: str | None, city: str) -> bool:
    """True se o endereco do place contem a cidade buscada (sem acento/caixa)."""
    if not address:
        # Sem endereco nao da pra confirmar; nao descarta (mantem benefit-of-doubt).
        return True
    return _norm(city) in _norm(address)


def _handle_from_instagram_url(url: str | None) -> str | None:
    """https://www.instagram.com/diego.ortopedia/ -> diego.ortopedia."""
    if not url:
        return None
    cleaned = url.split("?")[0].rstrip("/")
    if "instagram.com/" not in cleaned.lower():
        return None
    handle = cleaned.rsplit("/", 1)[-1].strip()
    # Ignora paths que nao sao perfis (reel, p, explore, etc.).
    if not handle or handle.lower() in {"reel", "p", "explore", "stories", "tv"}:
        return None
    return handle


async def _enrich_instagram_followers(competitors: list[Competitor]) -> int:
    """Preenche instagram_followers nos competitors que tem @ resolvido.

    Chama o actor de perfil do Instagram com a lista de usernames e mescla o
    followersCount de volta por handle. Retorna quantos perfis foram enriquecidos.
    """
    handle_by_comp: dict[str, Competitor] = {}
    usernames: list[str] = []
    for comp in competitors:
        handle = _handle_from_instagram_url(comp.instagram_url)
        if handle and handle.lower() not in handle_by_comp:
            handle_by_comp[handle.lower()] = comp
            usernames.append(handle)

    if not usernames:
        return 0

    actor = _actor_path(settings.APIFY_INSTAGRAM_FOLLOWERS_ACTOR)
    url = f"{_BASE}/{actor}/run-sync-get-dataset-items"
    body = {"usernames": usernames}

    async with httpx.AsyncClient(timeout=settings.APIFY_TIMEOUT_SECONDS) as client:
        response = await client.post(
            url,
            params={
                "token": settings.APIFY_TOKEN,
                "format": "json",
                "clean": "true",
            },
            json=body,
        )

    if response.status_code not in (200, 201):
        logger.warning(
            "Apify Instagram returned %s: %s",
            response.status_code,
            _extract_error(response),
        )
        return 0

    try:
        items = response.json()
    except ValueError:
        return 0
    if not isinstance(items, list):
        return 0

    enriched = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        handle = _first_str(item, ("username", "handle", "ownerUsername"))
        followers = _as_int(
            _first_val(
                item,
                ("followersCount", "followers", "followersCountText", "edge_followed_by"),
            )
        )
        if handle is None or followers is None:
            continue
        comp = handle_by_comp.get(handle.lower())
        if comp is not None and comp.instagram_followers is None:
            comp.instagram_followers = followers
            enriched += 1
    return enriched


async def _enrich_site_snippets(competitors: list[Competitor]) -> int:
    """Le o site de cada concorrente (fetch direto, gratis) e extrai um sinal de
    posicionamento (titulo + meta description + primeiro H1). Best-effort por
    site; retorna quantos foram lidos. Materia-prima para copy/posicionamento."""
    targets = [c for c in competitors if c.website]
    if not targets:
        return 0

    async def one(comp: Competitor):
        snippet = await _fetch_site_snippet(comp.website or "")
        if snippet:
            comp.site_snippet = snippet
            return 1
        return 0

    results = await asyncio.gather(
        *(one(c) for c in targets), return_exceptions=True
    )
    return sum(r for r in results if isinstance(r, int))


async def _fetch_site_snippet(url: str) -> str | None:
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=True, headers=headers
        ) as client:
            r = await client.get(url)
    except httpx.HTTPError:
        return None
    if r.status_code != 200 or not r.text:
        return None
    html = r.text[:200000]
    title = _re_first(r"<title[^>]*>(.*?)</title>", html)
    desc = _re_first(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html
    ) or _re_first(
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', html
    )
    h1 = _re_first(r"<h1[^>]*>(.*?)</h1>", html)
    parts = [p for p in (title, desc, h1) if p]
    if not parts:
        return None
    # Deduplica e limita.
    seen: list[str] = []
    for p in parts:
        p = _clean_html_text(p)
        if p and p not in seen:
            seen.append(p)
    snippet = " | ".join(seen)
    return snippet[:260] if snippet else None


def _re_first(pattern: str, text: str) -> str | None:
    import re

    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else None


def _clean_html_text(text: str) -> str:
    import html as _html
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return " ".join(text.split())


async def fetch_meta_ads(
    *,
    search_term: str | None,
    limit: int,
) -> tuple[list[MetaAd], list[str]]:
    """Conta/colhe anuncios ativos na Meta Ad Library (BR) por termo, via Apify.

    A API oficial da Meta volta vazia p/ anuncio comercial BR; o scraper le a UI
    publica. Best-effort: qualquer erro -> lista vazia + nota. Usado para alimentar
    a secao Analise Meta com densidade de anuncios real do nicho.
    """
    if not settings.apify_meta_ads_enabled:
        return [], []
    term = (search_term or "").strip()
    if not term:
        return [], []

    actor = _actor_path(settings.APIFY_META_ADS_ACTOR)
    url = f"{_BASE}/{actor}/run-sync-get-dataset-items"
    library_url = (
        "https://www.facebook.com/ads/library/"
        "?active_status=active&ad_type=all&country=BR"
        f"&q={httpx.QueryParams({'q': term})['q']}"
        "&search_type=keyword_unordered"
    )
    count = max(1, min(limit, 50))
    body = {
        "startUrls": [{"url": library_url, "method": "GET"}],
        "count": count,
        "activeStatus": "active",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.APIFY_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                url,
                params={
                    "token": settings.APIFY_TOKEN,
                    "format": "json",
                    "clean": "true",
                },
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Apify Meta Ads request failed: %s", exc)
        return [], [f"Apify Meta Ads indisponivel (erro de conexao): {exc}"]

    if response.status_code not in (200, 201):
        detail = _extract_error(response)
        logger.warning("Apify Meta Ads returned %s: %s", response.status_code, detail)
        return [], [
            f"Apify Meta Ads retornou erro HTTP {response.status_code}: {detail}"
        ]

    try:
        items = response.json()
    except ValueError:
        return [], ["Apify Meta Ads retornou resposta nao-JSON."]
    if not isinstance(items, list) or not items:
        return [], [
            f"Apify Meta Ads: nenhum anuncio ativo encontrado para '{term}'."
        ]

    ads: list[MetaAd] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ad = _parse_meta_ad(item)
        if ad is not None:
            ads.append(ad)
    return ads, []


def _parse_meta_ad(item: dict[str, Any]) -> MetaAd | None:
    snapshot = item.get("snapshot") if isinstance(item.get("snapshot"), dict) else {}
    page_name = (
        _first_str(item, ("pageName", "page_name"))
        or _first_str(snapshot, ("page_name", "pageName"))
    )
    body = (
        _first_str(snapshot, ("body", "caption", "title"))
        or _first_str(item, ("adText", "body", "text"))
        or "Anuncio sem texto extraido"
    )
    if isinstance(item.get("snapshot", {}), dict):
        body_field = item["snapshot"].get("body")
        if isinstance(body_field, dict):
            body = body_field.get("text") or body
    cta = (
        _first_str(snapshot, ("cta_text", "ctaText"))
        or _first_str(item, ("ctaText", "cta_text"))
        or "Nao informado"
    )
    platforms = item.get("publisherPlatform") or item.get("publisher_platform")
    if isinstance(platforms, list):
        platforms_text = ", ".join(str(p) for p in platforms)
    else:
        platforms_text = str(platforms) if platforms else "Nao informado"
    started = _first_str(
        item, ("startDate", "start_date", "startDateFormatted", "adDeliveryStartTime")
    ) or "Nao informado"
    snapshot_url = (
        _first_str(item, ("url", "adLibraryUrl", "snapshotUrl"))
        or "https://www.facebook.com/ads/library/"
    )
    if page_name is None:
        page_name = "Pagina nao identificada"
    return MetaAd(
        page_name=page_name,
        body=body,
        cta_title=cta,
        platforms=platforms_text,
        started_at=started,
        snapshot_url=snapshot_url,
    )


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
