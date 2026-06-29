"""Servico do formulario de lacunas do onboarding (metodo AQF).

Responsabilidades:
- extrair os insumos estruturados do AQF a partir das transcricoes/documentos,
  marcando como null o que nao foi encontrado (vira lacuna no formulario);
- normalizar/validar o mapa de campos vindo do operador;
- renderizar os campos preenchidos como contexto para os agentes makers.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.schemas.intake import (
    INTAKE_FIELD_KEYS,
    INTAKE_FIELDS_BY_KEY,
    INTAKE_GROUPS,
)

if TYPE_CHECKING:
    from app.agents.runner import AgentRunner

logger = logging.getLogger(__name__)

_EXTRACTION_CHAR_LIMIT = 14000


def empty_intake_fields() -> dict[str, str | None]:
    return {key: None for key in INTAKE_FIELD_KEYS}


def normalize_intake_fields(raw: dict | None) -> dict[str, str | None]:
    """Garante todas as chaves canonicas; strip; vazio/placeholder -> None."""
    fields = empty_intake_fields()
    if not isinstance(raw, dict):
        return fields
    for key in INTAKE_FIELD_KEYS:
        value = raw.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "n/a", "na", "-"}:
            continue
        fields[key] = cleaned
    return fields


def load_intake_fields(intake_data: str | None) -> dict[str, str | None]:
    if not intake_data:
        return empty_intake_fields()
    try:
        parsed = json.loads(intake_data)
    except (json.JSONDecodeError, TypeError):
        return empty_intake_fields()
    if isinstance(parsed, dict) and isinstance(parsed.get("fields"), dict):
        return normalize_intake_fields(parsed["fields"])
    return normalize_intake_fields(parsed if isinstance(parsed, dict) else None)


def dump_intake_data(fields: dict[str, str | None], *, extracted: bool) -> str:
    return json.dumps(
        {"fields": normalize_intake_fields(fields), "extracted": bool(extracted)},
        ensure_ascii=False,
    )


def is_extracted(intake_data: str | None) -> bool:
    if not intake_data:
        return False
    try:
        parsed = json.loads(intake_data)
    except (json.JSONDecodeError, TypeError):
        return False
    return bool(isinstance(parsed, dict) and parsed.get("extracted"))


def _build_extraction_system_prompt() -> str:
    lines = [
        "Voce extrai dados objetivos do briefing e das transcricoes de um "
        "onboarding medico da Healz para preencher um formulario estruturado.",
        "Responda SOMENTE com um JSON valido (um unico objeto). As chaves devem "
        "ser EXATAMENTE as listadas abaixo. Para cada campo, use o valor "
        "encontrado no texto OU null quando o dado nao estiver presente. NUNCA "
        "invente, presuma ou generalize: na duvida, use null (vira pendencia "
        "para o operador preencher). Valores curtos e diretos, em portugues.",
        "",
        "Campos:",
    ]
    for group in INTAKE_GROUPS:
        lines.append(f"# {group.title}")
        for field in group.fields:
            hint = f" ({field.hint})" if field.hint else ""
            lines.append(f'- "{field.key}": {field.label}{hint}')
    return "\n".join(lines)


async def extract_intake_fields(
    *,
    transcription_context: str,
    runner: "AgentRunner",
    onboarding_id: int,
):
    """Roda o extrator e devolve (fields, run_result|None). Best-effort: em
    qualquer falha devolve campos vazios para o operador preencher do zero."""
    base = (transcription_context or "").strip()
    if not base or base.startswith("Nenhuma transcricao"):
        return empty_intake_fields(), None

    if len(base) > _EXTRACTION_CHAR_LIMIT:
        base = base[:_EXTRACTION_CHAR_LIMIT].rstrip()

    try:
        result = await runner.run(
            agent_name="intake_extractor",
            step_name="intake_extraction",
            system_prompt=_build_extraction_system_prompt(),
            user_prompt="Briefing e transcricoes do onboarding:\n" + base,
            response_format={"type": "json_object"},
            enable_web_search=False,
        )
    except Exception:  # noqa: BLE001 - extracao nunca bloqueia o fluxo
        logger.exception(
            "Extracao de intake falhou.", extra={"onboarding_id": onboarding_id}
        )
        return empty_intake_fields(), None

    try:
        data = json.loads(result.content) if result.content else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    return normalize_intake_fields(data if isinstance(data, dict) else None), result


def render_intake_context(fields: dict[str, str | None]) -> str | None:
    """Renderiza os campos preenchidos como bloco de contexto para os makers.

    So inclui campos com valor; lista as lacunas conhecidas ao final para que os
    agentes saibam o que tratar como pendencia (em vez de inventar)."""
    filled_sections: list[str] = []
    missing_labels: list[str] = []
    for group in INTAKE_GROUPS:
        rows: list[str] = []
        for field in group.fields:
            value = fields.get(field.key)
            if value:
                rows.append(f"- {field.label}: {value}")
            else:
                missing_labels.append(field.label)
        if rows:
            filled_sections.append(f"{group.title}:\n" + "\n".join(rows))

    if not filled_sections and not missing_labels:
        return None

    parts = [
        "DADOS ESTRUTURADOS DO ONBOARDING (validados pelo operador no formulario "
        "de lacunas). Trate-os como fonte 'Extraido do briefing' confiavel; "
        "prefira-os a inferencias."
    ]
    if filled_sections:
        parts.append("\n\n".join(filled_sections))
    if missing_labels:
        parts.append(
            "Campos ainda nao informados (trate como pendencia rastreavel, nao "
            "invente): " + ", ".join(missing_labels) + "."
        )
    return "\n\n".join(parts)
