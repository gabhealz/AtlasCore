"""Telemetria de custo: registra cada chamada de LLM e agrega por onboarding."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm_usage_event import LLMUsageEvent
from app.services.llm_pricing import estimate_cost

logger = logging.getLogger(__name__)


async def record_apify_usage(
    db: AsyncSession,
    *,
    onboarding_id: int,
    places: int = 0,
    ig_profiles: int = 0,
    meta_ads: int = 0,
) -> None:
    """Registra o custo da coleta Apify (Google Maps + Instagram + Meta Ads) como
    uma linha na telemetria, para aparecer somado no custo do onboarding.

    Apify e pay-per-result: custo = nº de itens coletados x preço unitário. Os
    'tokens' ficam zerados (nao e LLM). Best-effort: nunca quebra o pipeline."""
    if not (places or ig_profiles or meta_ads):
        return
    try:
        cost = (
            places * settings.APIFY_COST_PER_PLACE_USD
            + ig_profiles * settings.APIFY_COST_PER_IG_PROFILE_USD
            + meta_ads * settings.APIFY_COST_PER_META_AD_USD
        )
        db.add(
            LLMUsageEvent(
                onboarding_id=onboarding_id,
                step_name="apify_benchmark",
                agent_name="apify",
                model="apify-actor",
                input_tokens=0,
                output_tokens=0,
                web_searches=0,
                cost_usd=round(cost, 6),
            )
        )
        await db.commit()
    except Exception:  # noqa: BLE001 - telemetria nunca bloqueia o pipeline
        logger.exception(
            "Falha ao registrar uso de Apify (onboarding=%s).", onboarding_id
        )
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


async def record_usage(
    db: AsyncSession,
    *,
    onboarding_id: int,
    result,
    web_searches: int = 0,
) -> None:
    """Grava o uso real de uma chamada de agente. Best-effort: nunca quebra o
    pipeline e nunca contamina a transacao em caso de erro."""
    try:
        cost = estimate_cost(
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            web_searches=web_searches,
        )
        db.add(
            LLMUsageEvent(
                onboarding_id=onboarding_id,
                step_name=result.step_name,
                agent_name=result.agent_name,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                web_searches=web_searches,
                cost_usd=cost,
            )
        )
        await db.commit()
    except Exception:  # noqa: BLE001 - telemetria nunca bloqueia o pipeline
        logger.exception(
            "Falha ao registrar uso de LLM (onboarding=%s).", onboarding_id
        )
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


async def summarize_onboarding_cost(
    db: AsyncSession, onboarding_id: int
) -> dict:
    rows = (
        await db.execute(
            select(LLMUsageEvent)
            .where(LLMUsageEvent.onboarding_id == onboarding_id)
            .order_by(LLMUsageEvent.created_at)
        )
    ).scalars().all()

    by_step: dict[str, dict] = {}
    total_cost = 0.0
    total_input = 0
    total_output = 0
    total_searches = 0
    for row in rows:
        cost = float(row.cost_usd or 0)
        total_cost += cost
        total_input += row.input_tokens or 0
        total_output += row.output_tokens or 0
        total_searches += row.web_searches or 0
        bucket = by_step.setdefault(
            row.step_name,
            {
                "step_name": row.step_name,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            },
        )
        bucket["calls"] += 1
        bucket["input_tokens"] += row.input_tokens or 0
        bucket["output_tokens"] += row.output_tokens or 0
        bucket["cost_usd"] += cost

    return {
        "onboarding_id": onboarding_id,
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_web_searches": total_searches,
        "calls": len(rows),
        "by_step": [
            {**bucket, "cost_usd": round(bucket["cost_usd"], 6)}
            for bucket in by_step.values()
        ],
    }
