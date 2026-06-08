"""Tabela de precos de LLM e estimativa de custo por chamada.

Precos em USD por 1.000.000 de tokens (input/output). Ajuste conforme os precos
vigentes da OpenAI. A taxa de web_search e aproximada e configuravel via env.
"""

from app.core.config import settings

# USD por 1M de tokens.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
DEFAULT_PRICING = {"input": 2.00, "output": 8.00}


def _resolve_pricing(model: str | None) -> dict[str, float]:
    if not model:
        return DEFAULT_PRICING
    normalized = model.strip().lower()
    if normalized in MODEL_PRICING:
        return MODEL_PRICING[normalized]
    # Casa pelo prefixo conhecido mais longo (ex.: "gpt-4.1-mini-2025-..." ).
    best_key: str | None = None
    for key in MODEL_PRICING:
        if normalized.startswith(key) and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return MODEL_PRICING[best_key] if best_key else DEFAULT_PRICING


def estimate_cost(
    *,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    web_searches: int = 0,
) -> float:
    pricing = _resolve_pricing(model)
    cost = (max(0, input_tokens) / 1_000_000) * pricing["input"]
    cost += (max(0, output_tokens) / 1_000_000) * pricing["output"]
    cost += max(0, web_searches) * settings.LLM_WEB_SEARCH_FEE_USD
    return round(cost, 6)
