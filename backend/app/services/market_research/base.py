"""Estruturas comuns dos dados de mercado coletados e sua renderizacao.

Tudo aqui e dado puro + serializacao para o prompt. As chamadas HTTP ficam nos
clientes especificos (meta_ad_library.py, dataforseo.py, google_keywords.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


def _truncate(text: str, limit: int = 240) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _escape_cell(text: str) -> str:
    """Mantem o texto seguro dentro de uma celula de tabela Markdown."""
    return _truncate(text).replace("|", "/").replace("\n", " ") or (
        "Dado pendente de validacao externa"
    )


@dataclass(slots=True)
class KeywordMetric:
    keyword: str
    avg_monthly_searches: int | None
    cpc: float | None
    competition: str | None
    source: str
    location: str

    def volume_text(self) -> str:
        if self.avg_monthly_searches is None:
            return "Dado indisponivel apos pesquisa"
        return f"{self.avg_monthly_searches:,}".replace(",", ".")

    def cpc_text(self) -> str:
        if self.cpc is None:
            return "Dado indisponivel apos pesquisa"
        return f"R$ {self.cpc:.2f}".replace(".", ",")


@dataclass(slots=True)
class MetaAd:
    page_name: str
    body: str
    cta_title: str
    platforms: str
    started_at: str
    snapshot_url: str


@dataclass(slots=True)
class Competitor:
    """Concorrente real coletado do Google Maps (via Apify), com nota, nº de
    avaliações e links de redes sociais (Instagram/Facebook) extraídos do site."""

    name: str
    rating: float | None
    reviews_count: int | None
    category: str | None
    website: str | None
    instagram_url: str | None
    instagram_followers: int | None
    facebook_url: str | None
    address: str | None
    meta_ads_count: int | None = None

    def rating_text(self) -> str:
        if self.rating is None:
            return "Indisponivel"
        return f"{self.rating:.1f}".replace(".", ",")

    def reviews_text(self) -> str:
        if self.reviews_count is None:
            return "Indisponivel"
        return f"{self.reviews_count:,}".replace(",", ".")

    def followers_text(self) -> str:
        if self.instagram_followers is None:
            return "Indisponivel"
        return f"{self.instagram_followers:,}".replace(",", ".")

    def meta_ads_text(self) -> str:
        if self.meta_ads_count is None:
            return "Indisponivel"
        return f"{self.meta_ads_count:,}".replace(",", ".")


@dataclass(slots=True)
class CollectedMarketData:
    keywords: list[KeywordMetric] = field(default_factory=list)
    meta_ads: list[MetaAd] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Contadores de itens cobrados pela Apify (pay-per-result), para telemetria
    # de custo. Preenchidos pelo cliente Apify; usados pelo orquestrador.
    apify_places: int = 0
    apify_ig_profiles: int = 0
    apify_meta_ads: int = 0

    @property
    def has_data(self) -> bool:
        return bool(self.keywords or self.meta_ads or self.competitors)

    def to_prompt_context(self) -> str:
        """Renderiza o bloco que sera injetado no prompt do researcher.

        Retorna string vazia quando nao ha nenhum dado coletado, para que o
        orquestrador simplesmente nao injete contexto extra.
        """
        if not self.has_data and not self.notes:
            return ""

        today = date.today().strftime("%d/%m/%Y")
        lines: list[str] = [
            "DADOS DE MERCADO COLETADOS VIA API (Fonte externa verificada):",
            (
                "Os dados abaixo foram coletados automaticamente de fontes "
                "externas autenticadas nesta data (" + today + "). Trate-os como "
                "'Fonte externa verificada': use os numeros REAIS de Volume, CPC "
                "e os anuncios reais da Meta para preencher as tabelas de "
                "'Analise de Demanda Google' e 'Analise Meta', sempre citando a "
                "fonte indicada e a data " + today + ". Nao rebaixe estes dados "
                "para pendencia e nao os apresente como achismo."
            ),
        ]

        if self.sources_used:
            lines.append("Fontes ativas: " + ", ".join(self.sources_used) + ".")

        if self.competitors:
            lines.append("")
            lines.append(
                "Concorrentes reais (Google Maps - nota, nº de avaliações e "
                "seguidores do Instagram extraídos do perfil). Use estes nomes e "
                "numeros REAIS (verbatim) na tabela de concorrentes e na prova "
                "social; o link do Instagram resolve o @ de cada concorrente. "
                "NÃO re-busque nem altere estes números:"
            )
            lines.append(
                "| Concorrente | Nota Google | Avaliações | Instagram | "
                "Seguidores | Facebook | Site | Categoria |"
            )
            lines.append("|---|---|---|---|---|---|---|---|")
            for comp in self.competitors:
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            _escape_cell(comp.name),
                            comp.rating_text(),
                            comp.reviews_text(),
                            _escape_cell(comp.instagram_url or "Indisponivel"),
                            comp.followers_text(),
                            _escape_cell(comp.facebook_url or "Indisponivel"),
                            _escape_cell(comp.website or "Indisponivel"),
                            _escape_cell(comp.category or "Nao informado"),
                        )
                    )
                    + " |"
                )

        if self.keywords:
            lines.append("")
            lines.append("Palavras-chave (volume mensal e CPC reais):")
            lines.append(
                "| Palavra-chave | Volume | CPC | Concorrencia | Fonte | Regiao |"
            )
            lines.append("|---|---|---|---|---|---|")
            for kw in self.keywords:
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            _escape_cell(kw.keyword),
                            kw.volume_text(),
                            kw.cpc_text(),
                            _escape_cell(kw.competition or "Nao informado"),
                            _escape_cell(kw.source),
                            _escape_cell(kw.location),
                        )
                    )
                    + " |"
                )

        if self.meta_ads:
            lines.append("")
            lines.append("Anuncios ativos na Meta Ad Library (reais):")
            lines.append(
                "| Pagina | Texto do anuncio | CTA | Plataformas | Inicio | "
                "Link/snapshot |"
            )
            lines.append("|---|---|---|---|---|---|")
            for ad in self.meta_ads:
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            _escape_cell(ad.page_name),
                            _escape_cell(ad.body),
                            _escape_cell(ad.cta_title or "Nao informado"),
                            _escape_cell(ad.platforms or "Nao informado"),
                            _escape_cell(ad.started_at or "Nao informado"),
                            _escape_cell(ad.snapshot_url or "Nao informado"),
                        )
                    )
                    + " |"
                )

        if self.notes:
            lines.append("")
            lines.append("Observacoes de coleta (fontes indisponiveis/limitadas):")
            for note in self.notes:
                lines.append(f"- {note}")

        return "\n".join(lines)
