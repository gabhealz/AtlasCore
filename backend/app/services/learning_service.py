"""Loop de aprendizado do pipeline (Nivel 1).

O sistema "aprende" sem treinar modelos: recupera, por especialidade, os
documentos que ja foram APROVADOS na revisao humana (exemplares de ouro) e as
licoes dos feedbacks de recusa, injetando isso como referencia no prompt do
agente da etapa. Quanto mais a base de clientes cresce, mais forte fica.

Nao depende de migracao: usa generated_documents (aprovados) e pipeline_events
(feedbacks de recusa), que ja sao persistidos.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generated_document import GeneratedDocument
from app.models.onboarding import Onboarding
from app.models.pipeline_event import PipelineEvent

logger = logging.getLogger(__name__)

DOCUMENT_REVIEW_STATUS_APPROVED = "APPROVED"
MAX_EXEMPLARS = 2
EXEMPLAR_CHAR_LIMIT = 3000
MAX_LESSONS = 3
LESSON_SCAN_LIMIT = 25


def _truncate(text: str | None, limit: int) -> str:
    value = text or ""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n[...trecho truncado para referencia...]"


async def _fetch_approved_exemplars(
    db: AsyncSession,
    *,
    specialty_like: str,
    step_name: str,
    exclude_onboarding_id: int,
) -> list[GeneratedDocument]:
    result = await db.execute(
        select(GeneratedDocument)
        .join(Onboarding, GeneratedDocument.onboarding_id == Onboarding.id)
        .where(
            Onboarding.specialty.ilike(specialty_like),
            GeneratedDocument.step_name == step_name,
            GeneratedDocument.review_status == DOCUMENT_REVIEW_STATUS_APPROVED,
            GeneratedDocument.onboarding_id != exclude_onboarding_id,
        )
        .order_by(GeneratedDocument.updated_at.desc())
        .limit(MAX_EXEMPLARS)
    )
    return list(result.scalars().all())


async def _fetch_rejection_lessons(
    db: AsyncSession,
    *,
    specialty_like: str,
    step_name: str,
) -> list[str]:
    result = await db.execute(
        select(PipelineEvent)
        .join(Onboarding, PipelineEvent.onboarding_id == Onboarding.id)
        .where(
            Onboarding.specialty.ilike(specialty_like),
            PipelineEvent.step_name == step_name,
        )
        .order_by(PipelineEvent.created_at.desc())
        .limit(LESSON_SCAN_LIMIT)
    )
    lessons: list[str] = []
    seen: set[str] = set()
    for event in result.scalars().all():
        payload = event.payload if isinstance(event.payload, dict) else {}
        feedback = payload.get("review_feedback")
        if isinstance(feedback, str):
            cleaned = feedback.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                lessons.append(cleaned)
        if len(lessons) >= MAX_LESSONS:
            break
    return lessons


async def build_learning_context(
    db: AsyncSession,
    *,
    onboarding: Onboarding,
    step_name: str,
) -> str | None:
    """Monta o bloco de aprendizado para a etapa atual. Best-effort: qualquer
    falha resulta em contexto vazio, nunca bloqueia o pipeline."""

    specialty = (onboarding.specialty or "").strip()
    if not specialty:
        return None

    specialty_like = f"%{specialty}%"
    sections: list[str] = []

    try:
        exemplars = await _fetch_approved_exemplars(
            db,
            specialty_like=specialty_like,
            step_name=step_name,
            exclude_onboarding_id=onboarding.id,
        )
    except Exception:  # noqa: BLE001 - aprendizado e best-effort
        logger.exception(
            "Falha ao recuperar exemplares aprovados para aprendizado.",
            extra={"onboarding_id": onboarding.id, "step_name": step_name},
        )
        exemplars = []

    if exemplars:
        parts = [
            f"### Exemplar aprovado (titulo: {doc.title})\n"
            f"{_truncate(doc.markdown_content, EXEMPLAR_CHAR_LIMIT)}"
            for doc in exemplars
        ]
        sections.append(
            "APRENDIZADO HEALZ - exemplares desta MESMA especialidade "
            f"({specialty}) que ja passaram pela aprovacao humana. Use-os apenas "
            "como referencia de profundidade, estrutura e tom de qualidade; NAO "
            "copie dados de outro medico/cliente, apenas o padrao:\n\n"
            + "\n\n".join(parts)
        )

    try:
        lessons = await _fetch_rejection_lessons(
            db,
            specialty_like=specialty_like,
            step_name=step_name,
        )
    except Exception:  # noqa: BLE001 - aprendizado e best-effort
        logger.exception(
            "Falha ao recuperar licoes de feedback para aprendizado.",
            extra={"onboarding_id": onboarding.id, "step_name": step_name},
        )
        lessons = []

    if lessons:
        bullets = "\n".join(f"- {lesson}" for lesson in lessons)
        sections.append(
            "LICOES DE REVISOES HUMANAS ANTERIORES nesta especialidade (ajustes "
            "que operadores ja pediram em etapas iguais; evite repetir esses "
            "problemas):\n" + bullets
        )

    if not sections:
        return None

    return "\n\n".join(sections)
