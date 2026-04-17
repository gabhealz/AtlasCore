"""Benchmark Agent — OpenAI Agents SDK implementation.

This module implements the Healz Benchmark Agent that processes
doctor onboarding transcripts through 5 sequential stages to
generate a complete market benchmarking document.

Requires OPENAI_API_KEY environment variable to be set.
"""

import json
import logging
from typing import Any

from app.config import get_settings
from app.prompts.benchmark_prompts import (
    PARSER_SYSTEM_PROMPT,
    BENCHMARK_ETAPA_1_PROMPT,
    BENCHMARK_ETAPA_2_PROMPT,
    BENCHMARK_ETAPA_3_PROMPT,
    BENCHMARK_ETAPA_4_PROMPT,
    BENCHMARK_ETAPA_5_PROMPT,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def parse_transcript(raw_text: str) -> dict[str, Any]:
    """Parse a raw transcript into structured data using GPT-4.1-nano.

    Args:
        raw_text: Raw text from a meeting transcription.

    Returns:
        Structured dict with extracted client data.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning mock parsed data")
        return _mock_parsed_data()

    from agents import Agent, Runner

    parser_agent = Agent(
        name="Transcript Parser",
        model="gpt-4.1-nano",
        instructions=PARSER_SYSTEM_PROMPT,
    )

    result = await Runner.run(parser_agent, raw_text[:50000])  # Limit to ~50K chars
    try:
        return json.loads(result.final_output)
    except json.JSONDecodeError:
        logger.error("Failed to parse agent output as JSON")
        return {"raw_output": result.final_output, "parse_error": True}


async def run_benchmark_pipeline(
    client_data: dict[str, Any],
    on_step_complete: callable = None,
) -> dict[str, Any]:
    """Run the complete 5-step benchmark pipeline.

    Args:
        client_data: Structured data from transcript parsing.
        on_step_complete: Optional callback(step_number, step_result) for progress tracking.

    Returns:
        Complete benchmark document as dict with all 5 sections.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning mock benchmark")
        return _mock_benchmark()

    from agents import Agent, WebSearchTool, Runner

    results = {}
    client_data_str = json.dumps(client_data, ensure_ascii=False, indent=2)

    # ─── Etapa 1: Definição do Objetivo ──────────────────────────────
    logger.info("Benchmark: Starting Etapa 1 — Definição do Objetivo")
    agent_e1 = Agent(
        name="Benchmark — Etapa 1",
        model="gpt-4.1-mini",
        instructions="Você é um estrategista de marketing digital para médicos da agência Healz.",
    )
    prompt_e1 = BENCHMARK_ETAPA_1_PROMPT.format(client_data=client_data_str)
    result_e1 = await Runner.run(agent_e1, prompt_e1)
    results["etapa_1_objetivo"] = {
        "title": "Definição do Objetivo",
        "content": result_e1.final_output,
    }
    if on_step_complete:
        await on_step_complete(1, results["etapa_1_objetivo"])

    # ─── Etapa 2: Pesquisa de Público + Personas ─────────────────────
    logger.info("Benchmark: Starting Etapa 2 — Público e Personas")
    agent_e2 = Agent(
        name="Benchmark — Etapa 2",
        model="gpt-4.1-mini",
        instructions="Você é um estrategista de marketing digital para médicos da agência Healz.",
    )
    prompt_e2 = BENCHMARK_ETAPA_2_PROMPT.format(
        client_data=client_data_str,
        etapa_1=results["etapa_1_objetivo"]["content"],
    )
    result_e2 = await Runner.run(agent_e2, prompt_e2)
    results["etapa_2_personas"] = {
        "title": "Pesquisa de Público e Personas",
        "content": result_e2.final_output,
    }
    if on_step_complete:
        await on_step_complete(2, results["etapa_2_personas"])

    # ─── Etapa 3: Captação Google (com WebSearch) ────────────────────
    logger.info("Benchmark: Starting Etapa 3 — Estratégia Google")
    agent_e3 = Agent(
        name="Benchmark — Etapa 3",
        model="gpt-4.1-mini",
        tools=[WebSearchTool()],
        instructions="Você é um pesquisador de mercado digital para médicos. Use web search para encontrar dados reais sobre concorrentes.",
    )
    etapas_anteriores = f"## Etapa 1\n{results['etapa_1_objetivo']['content']}\n\n## Etapa 2\n{results['etapa_2_personas']['content']}"
    prompt_e3 = BENCHMARK_ETAPA_3_PROMPT.format(
        client_data=client_data_str,
        etapas_anteriores=etapas_anteriores,
    )
    result_e3 = await Runner.run(agent_e3, prompt_e3)
    results["etapa_3_google"] = {
        "title": "Estratégia de Captação — Google",
        "content": result_e3.final_output,
    }
    if on_step_complete:
        await on_step_complete(3, results["etapa_3_google"])

    # ─── Etapa 4: Análise Meta (com WebSearch) ───────────────────────
    logger.info("Benchmark: Starting Etapa 4 — Análise Meta")
    agent_e4 = Agent(
        name="Benchmark — Etapa 4",
        model="gpt-4.1-mini",
        tools=[WebSearchTool()],
        instructions="Você é um pesquisador de mercado digital para médicos. Use web search para encontrar dados reais sobre anúncios e perfis.",
    )
    etapas_anteriores += f"\n\n## Etapa 3\n{results['etapa_3_google']['content']}"
    prompt_e4 = BENCHMARK_ETAPA_4_PROMPT.format(
        client_data=client_data_str,
        etapas_anteriores=etapas_anteriores,
    )
    result_e4 = await Runner.run(agent_e4, prompt_e4)
    results["etapa_4_meta"] = {
        "title": "Análise Meta — Captação e Autoridade",
        "content": result_e4.final_output,
    }
    if on_step_complete:
        await on_step_complete(4, results["etapa_4_meta"])

    # ─── Etapa 5: Síntese e Direcionamento ───────────────────────────
    logger.info("Benchmark: Starting Etapa 5 — Síntese")
    agent_e5 = Agent(
        name="Benchmark — Etapa 5",
        model="gpt-4.1-mini",
        instructions="Você é um estrategista sênior de marketing digital para médicos da agência Healz.",
    )
    etapas_anteriores += f"\n\n## Etapa 4\n{results['etapa_4_meta']['content']}"
    prompt_e5 = BENCHMARK_ETAPA_5_PROMPT.format(etapas_anteriores=etapas_anteriores)
    result_e5 = await Runner.run(agent_e5, prompt_e5)
    results["etapa_5_sintese"] = {
        "title": "Síntese e Direcionamento",
        "content": result_e5.final_output,
    }
    if on_step_complete:
        await on_step_complete(5, results["etapa_5_sintese"])

    logger.info("Benchmark: Pipeline completed successfully")
    return results


def _mock_parsed_data() -> dict:
    """Return mock parsed data when no API key is available."""
    return {
        "nome_medico": "Dr. Exemplo (dados mock — configure OPENAI_API_KEY)",
        "especialidade": "Urologia",
        "cidade": "Campinas",
        "estado": "SP",
        "foco_projeto": "captacao",
        "procedimentos_carro_chefe": ["Consulta urológica", "Cirurgia robótica"],
        "orcamento_midia": "R$ 2.000",
        "lacunas": ["API Key não configurada — dados são mock"],
    }


def _mock_benchmark() -> dict:
    """Return mock benchmark when no API key is available."""
    return {
        "etapa_1_objetivo": {
            "title": "Definição do Objetivo",
            "content": "⚠️ **Dados mock** — Configure OPENAI_API_KEY para gerar benchmark real.\n\n## Foco do Projeto\nCaptação pura de pacientes.\n\n## Procedimentos Carro-Chefe\n- Consulta urológica\n- Cirurgia robótica\n\n## Metas\n| KPI | Atual | Meta |\n|-----|-------|------|\n| Consultas/mês | 20 | 40 |\n| Faturamento | R$ 30k | R$ 60k |",
        },
        "etapa_2_personas": {
            "title": "Pesquisa de Público e Personas",
            "content": "⚠️ **Dados mock** — Configure OPENAI_API_KEY.\n\n## Persona 1 — João\nHomem, 45-65 anos, classe B, Campinas-SP.\n**Dor**: Problemas urinários recorrentes.\n**Emoção motriz**: Preocupação com a saúde.",
        },
        "etapa_3_google": {
            "title": "Estratégia de Captação — Google",
            "content": "⚠️ **Dados mock** — Configure OPENAI_API_KEY.\n\n## Palavras-chave\n| Termo | Volume estimado |\n|-------|-----------------|\n| urologista campinas | ~1.000/mês |\n\n## Concorrentes\nAnálise pendente (requer API key para web search).",
        },
        "etapa_4_meta": {
            "title": "Análise Meta — Captação e Autoridade",
            "content": "⚠️ **Dados mock** — Configure OPENAI_API_KEY.\n\nAnálise de anúncios e perfis pendente.",
        },
        "etapa_5_sintese": {
            "title": "Síntese e Direcionamento",
            "content": "⚠️ **Dados mock** — Configure OPENAI_API_KEY.\n\n## Recomendação Preliminar\n- **Canais**: Google + Meta\n- **Abordagem**: Captação direta com suporte de autoridade\n- **Foco**: Consulta urológica + Cirurgia robótica",
        },
    }
