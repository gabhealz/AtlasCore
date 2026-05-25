"""Coleta de dados de mercado para o onboarding com IA.

Esta camada roda ANTES da etapa de pesquisa do agente e busca dados REAIS em
fontes externas autenticadas (Meta Ad Library, DataForSEO, Google Ads Keyword
Planner). O resultado e injetado no prompt do researcher como "Fonte externa
verificada", para que volume/CPC e anuncios da Meta venham com numeros reais em
vez de apenas pendencias.

Degradacao segura: quando uma credencial nao esta configurada ou a chamada
falha, a fonte e ignorada e o pipeline continua exatamente como antes (apenas
com web_search). Nada aqui deve levantar excecao para o orquestrador.
"""

from app.services.market_research.base import (
    CollectedMarketData,
    KeywordMetric,
    MetaAd,
)
from app.services.market_research.collector import collect_market_data

__all__ = [
    "CollectedMarketData",
    "KeywordMetric",
    "MetaAd",
    "collect_market_data",
]
