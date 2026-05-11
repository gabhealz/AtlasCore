import json
import logging
import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.prompts import (
    build_researcher_system_prompt,
    build_reviewer_system_prompt,
)
from app.agents.runner import AgentRunner, AgentRunnerError, AgentRunResult
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.generated_document import GeneratedDocument
from app.models.onboarding import Onboarding
from app.models.uploaded_asset import UploadedAsset
from app.schemas.generated_document import GeneratedDocumentDraft
from app.schemas.html_document import GeneratedHtmlDocumentDraft
from app.schemas.reviewer import ReviewerDecision
from app.services.asset_service import AssetService
from app.services.generated_document_service import (
    DOCUMENT_REVIEW_STATUS_APPROVED,
    DOCUMENT_REVIEW_STATUS_AWAITING,
    GeneratedDocumentService,
)
from app.services.html_validation_service import (
    HTMLValidationError,
    validate_generated_html,
)
from app.services.pipeline_service import (
    PIPELINE_AWAITING_REVIEW_STATUS,
    PipelineService,
)

logger = logging.getLogger(__name__)

TEXT_ASSET_CHAR_LIMIT = 12000
REJECTED_DRAFT_FEEDBACK_CHAR_LIMIT = 6000
REVIEWER_AGENT_NAME = "reviewer"
REVIEWER_MAX_REWRITE_ATTEMPTS = 3
RESEARCHER_REQUIRED_SECTIONS = (
    "Resumo Executivo",
    "Perfil do Projeto",
    "Publico e Personas",
    "Analise de Demanda Google",
    "Benchmark de Concorrentes",
    "Matriz de Benchmark Competitivo",
    "Analise Meta",
    "Conteudo Organico",
    "Benchmarks e Viabilidade",
    "Oportunidades e Diferenciais",
    "Recomendacao Preliminar",
    "Dados Extraidos dos Anexos",
    "Pendencias para Preenchimento Humano",
    "Log de Consultas Externas",
)
RESEARCHER_REQUIRED_TABLE_MARKERS = (
    ("Perfil do Projeto", ("kpi", "situacao", "meta")),
    ("Analise de Demanda Google", ("palavra", "volume", "cpc")),
    ("Benchmark de Concorrentes", ("concorrente", "instagram", "meta")),
    ("Matriz de Benchmark Competitivo", ("concorrente", "url", "oportunidade")),
    ("Analise Meta", ("anuncio", "captacao", "autoridade")),
    ("Conteudo Organico", ("seguidores", "formato", "tema")),
)
RESEARCHER_RETRY_SKELETON = "\n".join(
    (
        "Copie exatamente este esqueleto de secoes e tabelas na proxima "
        "resposta. Nao renomeie headings, nao transforme tabela obrigatoria "
        "em paragrafo e nao use celulas vazias.",
        "",
        "## Resumo Executivo",
        "",
        "## Perfil do Projeto",
        "| KPI | Situacao atual | Meta 3 ou 6 meses | Fonte | Status |",
        "",
        "## Publico e Personas",
        "",
        "## Analise de Demanda Google",
        (
            "| Tipo | Palavra-chave | Intencao | Regiao | Volume | CPC | Fonte | "
            "URL/consulta | Data | Status |"
        ),
        "",
        "## Benchmark de Concorrentes",
        (
            "| Concorrente | Instagram | Meta | Destino | Copy | Funil | Fonte | "
            "URL/consulta | Data | Status |"
        ),
        "",
        "## Matriz de Benchmark Competitivo",
        (
            "| Concorrente | URL | Consulta que encontrou | Especialidade/foco | "
            "Oferta | Promessa/copy | CTA | Funil | Provas | Pontos fortes | "
            "Lacunas | Oportunidade | Status |"
        ),
        "",
        "## Analise Meta",
        "| Anuncio | Captacao | Autoridade | Fonte | Link/consulta | Data | Status |",
        "",
        "## Conteudo Organico",
        (
            "| Perfil | Seguidores | Formato | Tema | Tom | Frequencia | Fonte | "
            "Link/consulta | Data | Status |"
        ),
        "",
        "## Benchmarks e Viabilidade",
        "",
        "## Oportunidades e Diferenciais",
        "",
        "## Recomendacao Preliminar",
        "",
        "## Dados Extraidos dos Anexos",
        "| Campo | Valor | Fonte | Confianca |",
        "",
        "## Pendencias para Preenchimento Humano",
        "",
        "## Log de Consultas Externas",
        (
            "| Consulta executada | Fonte/ferramenta | Data | Titulo da pagina | "
            "URL | Resultado principal | Aproveitamento/descarte | Motivo | "
            "Status |"
        ),
    )
)
RESEARCHER_MISSING_SECTION_TEMPLATES = {
    "Resumo Executivo": (
        "Pesquisa externa parcial. O documento ainda depende de validacao "
        "humana e fontes complementares; dados sem fonte foram rebaixados "
        "para Dado pendente de validacao externa."
    ),
    "Perfil do Projeto": "\n".join(
        (
            "| KPI | Situacao atual | Meta 3 ou 6 meses | Fonte | Status |",
            "|---|---|---|---|---|",
            (
                "| Consultas | Dado pendente de validacao externa | Dado pendente "
                "de validacao externa | Briefing/anexos | Dado pendente de "
                "validacao externa |"
            ),
        )
    ),
    "Publico e Personas": (
        "Personas pendentes por falta de dados rastreaveis. Fonte principal: "
        "Extraido do briefing; validacao externa ainda pendente."
    ),
    "Analise de Demanda Google": "\n".join(
        (
            (
                "| Tipo | Palavra-chave | Intencao | Regiao | Volume | CPC | "
                "Fonte | URL/consulta | Data | Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|",
            (
                "| Pesquisa | Dado pendente de validacao externa | Dado pendente de "
                "validacao externa | Dado pendente de validacao externa | "
                "Dado indisponivel apos pesquisa | Dado indisponivel apos "
                "pesquisa | Google Keyword Planner | Consulta sugerida por "
                "especialidade + cidade | Dado pendente de validacao externa | "
                "Dado pendente de validacao externa |"
            ),
        )
    ),
    "Benchmark de Concorrentes": "\n".join(
        (
            (
                "| Concorrente | Instagram | Meta | Destino | Copy | Funil | "
                "Fonte | URL/consulta | Data | Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|",
            (
                "| Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa | Dado pendente "
                "de validacao externa | Dado pendente de validacao externa | "
                "Dado pendente de validacao externa | Google Search | Consulta "
                "sugerida por especialidade + cidade | Dado pendente de "
                "validacao externa | Dado pendente de validacao externa |"
            ),
        )
    ),
    "Matriz de Benchmark Competitivo": "\n".join(
        (
            (
                "| Concorrente | URL | Consulta que encontrou | Especialidade/foco | "
                "Oferta | Promessa/copy | CTA | Funil | Provas | Pontos fortes | "
                "Lacunas | Oportunidade | Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            (
                "| Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Consulta sugerida por especialidade + cidade | "
                "Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa | Dado pendente "
                "de validacao externa | Dado pendente de validacao externa | "
                "Nao encontrado nas fontes consultadas | Dado pendente de "
                "validacao externa | Dado pendente de validacao externa | "
                "Dado pendente de validacao externa | Dado pendente de "
                "validacao externa |"
            ),
        )
    ),
    "Analise Meta": "\n".join(
        (
            "| Anuncio | Captacao | Autoridade | Fonte | Link/consulta | Data | Status |",
            "|---|---|---|---|---|---|---|",
            (
                "| Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa | Meta Ads "
                "Library | Consulta sugerida por especialidade/cidade | Dado "
                "pendente de validacao externa | Dado pendente de validacao "
                "externa |"
            ),
        )
    ),
    "Conteudo Organico": "\n".join(
        (
            (
                "| Perfil | Seguidores | Formato | Tema | Tom | Frequencia | "
                "Fonte | Link/consulta | Data | Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|",
            (
                "| Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa | Dado pendente "
                "de validacao externa | Dado pendente de validacao externa | "
                "Dado pendente de validacao externa | Instagram | Consulta "
                "sugerida por perfil/concorrente | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa |"
            ),
        )
    ),
    "Benchmarks e Viabilidade": (
        "CPL, CAC, CPC e conversoes devem ser tratados como Benchmark interno "
        "Healz ou Benchmark publico de mercado somente quando houver fonte; "
        "dados locais permanecem como Dado pendente de validacao externa."
    ),
    "Oportunidades e Diferenciais": (
        "Sem concorrentes verificados suficientes, registrar lacuna de dados "
        "competitivos e hipoteses a validar, sem afirmar oportunidade definitiva."
    ),
    "Recomendacao Preliminar": (
        "Hipotese de canais a validar apos pesquisa externa complementar. Sem "
        "base suficiente para recomendar canal definitivo."
    ),
    "Dados Extraidos dos Anexos": "\n".join(
        (
            "| Campo | Valor | Fonte | Confianca |",
            "|---|---|---|---|",
            (
                "| Especialidade | Dado pendente de validacao externa | Extraido do "
                "briefing | Media |"
            ),
        )
    ),
    "Pendencias para Preenchimento Humano": (
        "Confirmar metas, ticket medio, procedimentos foco, raio de atendimento, "
        "orcamento de midia, links oficiais, concorrentes conhecidos e acesso a "
        "fontes externas."
    ),
    "Log de Consultas Externas": "\n".join(
        (
            (
                "| Consulta executada | Fonte/ferramenta | Data | Titulo da pagina | "
                "URL | Resultado principal | Aproveitamento/descarte | Motivo | "
                "Status |"
            ),
            "|---|---|---|---|---|---|---|---|---|",
            (
                "| Consulta sugerida por especialidade + cidade | Google Search | "
                "Dado pendente de validacao externa | Dado pendente de validacao "
                "externa | Dado pendente de validacao externa | Dado pendente "
                "de validacao externa | Descartado | Pesquisa nao executada "
                "ou nao verificavel no documento gerado | Pesquisa nao verificavel |"
            ),
        )
    ),
}
RESEARCHER_GENERIC_PATTERNS = (
    "diversas especialidades",
    "procedimentos especificos que a clinica deseja destacar",
    "maria silva",
    "joao pereira",
    "executiva de marketing",
    "advogado",
    "meta de 300 consultas",
    "r$ 150.000",
    "cpl): r$ 20",
    "cac): r$ 100",
    "existem concorrentes estabelecidos",
    "ha espaco para diferenciacao",
    "provavelmente",
    "pode converter bem",
    "falha de pesquisa externa: ainda nao realizada",
    "falha de pesquisa externa ainda nao realizada",
    "canais recomendados:",
    "lacuna identificada na concorrencia digital",
)
RESEARCHER_EVIDENCE_TERMS = (
    "Extraido do briefing",
    "Fonte externa verificada",
    "benchmark publico de mercado",
    "Benchmark interno Healz",
    "Dado pendente de validacao externa",
    "Nao encontrado nas fontes consultadas",
    "Dado indisponivel apos pesquisa",
)


@dataclass(frozen=True, slots=True)
class MakerStep:
    step_name: str
    agent_name: str
    document_kind: str
    prompt_builder: Callable[[], str]
    output_kind: str = "markdown"


class ResearcherQualityError(ValueError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("\n".join(issues))


MAKER_STEPS: tuple[MakerStep, ...] = (
    MakerStep(
        step_name="researcher",
        agent_name="researcher",
        document_kind="research_report",
        prompt_builder=build_researcher_system_prompt,
    ),
)

STEP_BY_NAME = {step.step_name: step for step in MAKER_STEPS}
STEP_ORDER = {step.step_name: index for index, step in enumerate(MAKER_STEPS)}


def get_maker_step(step_name: str) -> MakerStep | None:
    return STEP_BY_NAME.get(step_name)


def get_next_step_name(step_name: str) -> str | None:
    step_index = STEP_ORDER.get(step_name)
    if step_index is None:
        return None

    next_index = step_index + 1
    if next_index >= len(MAKER_STEPS):
        return None

    return MAKER_STEPS[next_index].step_name


def get_step_output_kind(step_name: str) -> str:
    step = get_maker_step(step_name)
    return step.output_kind if step is not None else "markdown"


def _resolve_pipeline_step(start_from_step: str | None) -> MakerStep:
    if start_from_step is None:
        return MAKER_STEPS[0]

    step = get_maker_step(start_from_step)
    if step is None:
        raise ValueError(f"Etapa de pipeline desconhecida: {start_from_step}.")

    return step


def _build_generated_document_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "generated_document",
            "strict": True,
            "schema": GeneratedDocumentDraft.model_json_schema(),
        },
    }


def _build_generated_html_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "generated_html_document",
            "strict": True,
            "schema": GeneratedHtmlDocumentDraft.model_json_schema(),
        },
    }


def _build_reviewer_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "reviewer_decision",
            "strict": True,
            "schema": ReviewerDecision.model_json_schema(),
        },
    }


def _truncate_text(content: str, *, limit: int = TEXT_ASSET_CHAR_LIMIT) -> str:
    normalized = content.strip()
    if len(normalized) <= limit:
        return normalized

    return f"{normalized[:limit].rstrip()}\n\n[conteudo truncado para o MVP]"


def _resolve_runner_model(runner: AgentRunner | Any) -> str:
    model = getattr(runner, "model", "")
    return model if isinstance(model, str) else ""


async def _load_onboarding(
    *,
    db: AsyncSession,
    onboarding_id: int,
) -> Onboarding | None:
    result = await db.execute(select(Onboarding).where(Onboarding.id == onboarding_id))
    return result.scalars().first()


async def _load_transcription_assets(
    *,
    db: AsyncSession,
    onboarding_id: int,
) -> list[UploadedAsset]:
    result = await db.execute(
        select(UploadedAsset)
        .where(
            UploadedAsset.onboarding_id == onboarding_id,
            UploadedAsset.asset_kind == "transcription",
        )
        .order_by(UploadedAsset.created_at.asc(), UploadedAsset.id.asc())
    )
    return result.scalars().all()


async def _build_transcription_context(
    *,
    db: AsyncSession,
    onboarding_id: int,
    asset_service: AssetService,
) -> str:
    assets = await _load_transcription_assets(db=db, onboarding_id=onboarding_id)
    if not assets:
        return "Nenhuma transcricao ou documento base foi anexado ao onboarding."

    sections: list[str] = []
    for asset in assets:
        extension = Path(asset.original_filename).suffix.lower()
        if extension == ".txt":
            content = asset_service.read_text_object(asset.object_key)
            excerpt = _truncate_text(content)
            sections.append(
                f"### {asset.original_filename}\n"
                f"{excerpt or '[arquivo vazio apos leitura]'}"
            )
            continue

        if extension == ".pdf":
            content = asset_service.read_pdf_object(asset.object_key)
            excerpt = _truncate_text(content)
            sections.append(
                f"### {asset.original_filename}\n"
                f"{excerpt or '[PDF sem texto extraivel automaticamente]'}"
            )
            continue

        if extension == ".docx":
            content = asset_service.read_docx_object(asset.object_key)
            excerpt = _truncate_text(content)
            sections.append(
                f"### {asset.original_filename}\n"
                f"{excerpt or '[DOCX sem texto extraivel automaticamente]'}"
            )
            continue

        sections.append(
            f"### {asset.original_filename}\n"
            "[Arquivo anexado, mas sem estrategia de leitura automatica "
            "nesta historia.]"
        )

    return "\n\n".join(sections)


def _select_documents_for_step(
    *,
    step: MakerStep,
    previous_documents: list[dict[str, str]],
) -> list[dict[str, str]]:
    if step.output_kind == "html":
        allowed_document_kinds = {"research_report", "strategy_plan", "copy_deck"}
        return [
            document
            for document in previous_documents
            if document["document_kind"] in allowed_document_kinds
        ]

    return previous_documents


def _serialize_document_for_prompt(
    document: GeneratedDocument,
) -> dict[str, str]:
    return {
        "document_kind": document.document_kind,
        "title": document.title,
        "markdown_content": document.markdown_content,
    }


def _build_previous_documents_for_step(
    *,
    step: MakerStep,
    approved_documents: list[GeneratedDocument],
) -> list[dict[str, str]]:
    current_step_index = STEP_ORDER[step.step_name]
    ordered_documents = sorted(
        approved_documents,
        key=lambda document: STEP_ORDER.get(document.step_name, len(MAKER_STEPS)),
    )
    return [
        _serialize_document_for_prompt(document)
        for document in ordered_documents
        if STEP_ORDER.get(document.step_name, len(MAKER_STEPS)) < current_step_index
    ]


def _build_step_response_format(step: MakerStep) -> dict[str, Any]:
    if step.output_kind == "html":
        return _build_generated_html_response_format()

    return _build_generated_document_response_format()


def _parse_step_output(
    *,
    step: MakerStep,
    raw_content: str,
) -> GeneratedDocumentDraft | GeneratedHtmlDocumentDraft:
    if step.output_kind == "html":
        return GeneratedHtmlDocumentDraft.model_validate_json(raw_content)

    try:
        return GeneratedDocumentDraft.model_validate_json(raw_content)
    except ValidationError:
        if step.output_kind == "markdown":
            stripped_content = raw_content.strip()
            recovered_draft = _recover_generated_document_from_json(
                stripped_content
            )
            if recovered_draft is not None:
                return recovered_draft

            if not stripped_content or stripped_content.startswith(("{", "[")):
                logger.warning(
                    "Invalid structured markdown agent output for step %s. "
                    "raw_output_excerpt=%r",
                    step.step_name,
                    stripped_content[:2000],
                )
                raise

            return _parse_markdown_step_output(
                step=step,
                raw_content=raw_content,
            )

        raise


def _recover_generated_document_from_json(
    raw_content: str,
) -> GeneratedDocumentDraft | None:
    try:
        parsed_content = json.loads(raw_content)
    except json.JSONDecodeError:
        return _recover_generated_document_from_json_like_text(raw_content)

    if not isinstance(parsed_content, dict):
        return None

    title = parsed_content.get("title")
    markdown_content = parsed_content.get("markdown_content")
    if not isinstance(title, str) or not isinstance(markdown_content, str):
        return _recover_generated_document_from_json_like_text(raw_content)

    return GeneratedDocumentDraft(
        title=title,
        markdown_content=markdown_content,
    )


def _recover_generated_document_from_json_like_text(
    raw_content: str,
) -> GeneratedDocumentDraft | None:
    title_match = re.search(r'"title"\s*:\s*"(?P<title>[^"]+)"', raw_content)
    markdown_match = re.search(r'"markdown_content"\s*:\s*"', raw_content)
    if title_match is None or markdown_match is None:
        return None

    markdown_start = markdown_match.end()
    markdown_end = raw_content.rfind('"}')
    if markdown_end <= markdown_start:
        markdown_end = raw_content.rfind('"')
    if markdown_end <= markdown_start:
        markdown_end = len(raw_content)

    title = _unescape_json_like_text(title_match.group("title"))
    markdown_content = _unescape_json_like_text(
        raw_content[markdown_start:markdown_end]
    )
    return GeneratedDocumentDraft(
        title=title,
        markdown_content=markdown_content,
    )


def _unescape_json_like_text(value: str) -> str:
    return (
        value.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\/", "/")
        .replace("\\\\", "\\")
    )


def _parse_markdown_step_output(
    *,
    step: MakerStep,
    raw_content: str,
) -> GeneratedDocumentDraft:
    stripped_content = raw_content.strip()
    if not stripped_content:
        raise ValueError("Markdown step output is blank.")

    title = _extract_markdown_title(stripped_content) or step.document_kind.replace(
        "_",
        " ",
    ).title()
    return GeneratedDocumentDraft(
        title=title,
        markdown_content=stripped_content,
    )


def _extract_markdown_title(markdown_content: str) -> str | None:
    for line in markdown_content.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("# "):
            title = stripped_line.lstrip("#").strip()
            return title or None

    return None


def _extract_document_content(
    *,
    step: MakerStep,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft,
) -> str:
    if step.output_kind == "html":
        html_draft = draft
        if not isinstance(html_draft, GeneratedHtmlDocumentDraft):
            raise ValueError("Invalid HTML draft instance.")
        return html_draft.html_content

    markdown_draft = draft
    if not isinstance(markdown_draft, GeneratedDocumentDraft):
        raise ValueError("Invalid markdown draft instance.")
    return markdown_draft.markdown_content


def _build_output_instruction(step: MakerStep) -> str:
    if step.output_kind == "html":
        return (
            "Responda em portugues do Brasil. O campo `html_content` deve conter "
            "um documento HTML completo, com `<!DOCTYPE html>`, `<html>`, "
            "`<body>` e CSS interno, pronto para uso sem dependencias externas."
        )

    instruction = (
        "Responda em portugues do Brasil, com conteudo objetivo, acionavel e "
        "pronto para revisao humana. O campo `markdown_content` deve conter "
        "Markdown valido e completo."
    )
    if step.step_name != "researcher":
        return instruction

    return (
        f"{instruction}\n\n"
        "Para esta etapa, o campo `markdown_content` deve seguir exatamente "
        "este esqueleto minimo de headings e tabelas; complete dados ausentes "
        "com pendencias rastreaveis, nunca omitindo secoes:\n"
        f"{RESEARCHER_RETRY_SKELETON}"
    )


def _build_onboarding_data_inventory() -> str:
    return (
        "Inventario de dados esperados para enriquecer o onboarding Healz:\n"
        "- Identificacao: nome do medico, CRM, RQE, especialidade, "
        "subespecialidade, cidade, estado, bairros/regiao de atuacao, "
        "enderecos, telemedicina, site, Instagram, Doctoralia/Google Business.\n"
        "- Atendimento e oferta: valor da consulta, formas de pagamento, "
        "convenios, reembolso, retorno incluso e prazo, duracao da consulta, "
        "politica de cancelamento, horarios, existencia de secretaria, tempo "
        "medio de resposta no WhatsApp.\n"
        "- Servicos: procedimentos carro-chefe, esteira completa de servicos, "
        "ticket medio por consulta/procedimento/cirurgia, margem quando "
        "disponivel, capacidade operacional mensal.\n"
        "- Objetivos: foco em captacao, autoridade ou misto; meta de pacientes, "
        "procedimentos e faturamento; horizonte de 3 ou 6 meses; orcamento de "
        "midia; prioridades comerciais.\n"
        "- Publico: faixas etarias, genero quando relevante, poder aquisitivo, "
        "regioes de origem, dores, medos, desejos, objecoes, nivel de "
        "consciencia e nivel de sofisticacao.\n"
        "- Mercado: keywords locais, volume de busca, CPC, CPL, concorrentes, "
        "provas sociais, anuncios ativos, funis usados, Meta/Instagram, "
        "lacunas de comunicacao e oportunidades.\n"
        "- Assets: fotos disponiveis, depoimentos reais, videos, materiais de "
        "curriculo/formacao, links e documentos anexados.\n\n"
        "Ao ler os anexos, extraia tudo que conseguir desse inventario. "
        "Nunca deixe uma lacuna invisivel: ao final do documento, inclua uma "
        "secao 'Dados extraidos dos anexos' e uma secao 'Pendencias para "
        "preenchimento humano', agrupando perguntas objetivas por prioridade."
    )


def _build_maker_user_prompt(
    *,
    step: MakerStep,
    onboarding: Onboarding,
    transcription_context: str,
    previous_documents: list[dict[str, str]],
    review_feedback: str | None = None,
    human_feedback: str | None = None,
    step_specific_context: str | None = None,
) -> str:
    previous_documents_block = ""
    selected_documents = _select_documents_for_step(
        step=step,
        previous_documents=previous_documents,
    )
    if selected_documents:
        previous_sections = []
        for document in selected_documents:
            previous_sections.append(
                "## Documento anterior\n"
                f"Tipo interno: {document['document_kind']}\n"
                f"Titulo: {document['title']}\n"
                f"Conteudo:\n{document['markdown_content']}"
            )
        previous_documents_block = (
            "\n\nDocumentos anteriores do pipeline:\n" + "\n\n".join(previous_sections)
        )

    step_specific_context_block = ""
    if step_specific_context:
        step_specific_context_block = f"\n\n{step_specific_context}"

    human_feedback_block = ""
    if human_feedback:
        human_feedback_block = (
            "\n\nFeedback humano da revisao anterior para esta etapa:\n"
            f"{human_feedback.strip()}"
        )

    review_feedback_block = ""
    if review_feedback:
        review_feedback_block = (
            "\n\nFeedback do checker CFM para esta reescrita:\n"
            f"{review_feedback.strip()}"
        )
    web_search_status = (
        "habilitada e obrigatoria"
        if step.step_name == "researcher" and settings.OPENAI_ENABLE_WEB_SEARCH
        else "nao habilitada"
    )

    return (
        "Contexto do onboarding Healz:\n"
        f"Medico: {onboarding.doctor_name}\n"
        f"Especialidade: {onboarding.specialty or 'Nao informada'}\n"
        f"Publico-alvo: {onboarding.target_audience or 'Nao informado'}\n"
        f"Diferenciais: {onboarding.differentials or 'Nao informados'}\n"
        f"Tom de voz: {onboarding.tone_of_voice or 'Nao informado'}\n\n"
        f"Pesquisa web externa nesta chamada: {web_search_status}\n\n"
        f"{_build_onboarding_data_inventory()}\n\n"
        "Transcricoes e documentos base:\n"
        f"{transcription_context}"
        f"{previous_documents_block}"
        f"{step_specific_context_block}"
        f"{human_feedback_block}"
        f"{review_feedback_block}\n\n"
        f"{_build_output_instruction(step)}"
    )


def _build_reviewer_user_prompt(
    *,
    onboarding: Onboarding,
    step: MakerStep,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft,
) -> str:
    content_label = "HTML" if step.output_kind == "html" else "Markdown"
    document_content = _extract_document_content(step=step, draft=draft)
    web_search_enabled = (
        step.step_name == "researcher" and settings.OPENAI_ENABLE_WEB_SEARCH
    )
    return (
        "Audite este documento do pipeline Healz contra regras de publicidade "
        "medica.\n"
        f"Medico: {onboarding.doctor_name}\n"
        f"Especialidade: {onboarding.specialty or 'Nao informada'}\n"
        f"Etapa: {step.step_name}\n"
        f"Tipo interno: {step.document_kind}\n"
        "Pesquisa web habilitada para esta etapa: "
        f"{'sim' if web_search_enabled else 'nao'}\n"
        f"Titulo: {draft.title}\n\n"
        f"Documento em {content_label}:\n"
        f"{document_content}\n\n"
        "Aprove apenas se o texto nao contiver violacoes obvias de compliance. "
        "Se reprovar, devolva instrucoes objetivas para reescrita sem inventar "
        "novos fatos."
    )


def _build_rejected_draft_context(
    *,
    step: MakerStep,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft,
) -> str:
    content = _extract_document_content(step=step, draft=draft)
    excerpt = _truncate_text(content, limit=REJECTED_DRAFT_FEEDBACK_CHAR_LIMIT)
    return (
        "Documento anterior rejeitado para corrigir, sem recomecar do zero:\n"
        f"Titulo anterior: {draft.title}\n"
        f"Conteudo anterior limitado:\n{excerpt}\n\n"
        "Corrija o documento anterior usando o feedback abaixo. Preserve o que "
        "estiver rastreavel, complete secoes/tabelas ausentes e remova ou "
        "rebaixe para pendencia qualquer dado sem fonte. Seja economico: nao "
        "explique o processo, apenas entregue o JSON final corrigido."
    )


def _build_rewrite_feedback(
    review: ReviewerDecision,
    *,
    step: MakerStep | None = None,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft | None = None,
) -> str:
    parts: list[str] = []
    if step is not None and draft is not None:
        parts.append(_build_rejected_draft_context(step=step, draft=draft))
    if review.feedback_summary:
        parts.append(f"Resumo do checker: {review.feedback_summary}")
    if review.violations:
        violations = "; ".join(review.violations)
        parts.append(f"Violacoes encontradas: {violations}")
    if review.rewrite_instructions:
        parts.append(f"Instrucoes de reescrita: {review.rewrite_instructions}")

    if not parts:
        return (
            "Ajuste o texto para remover violacoes de compliance medico, sem "
            "prometer cura, garantir resultados ou inventar claims nao suportados."
        )

    return "\n".join(parts)


def _normalize_for_quality_checks(content: str) -> str:
    return (
        content.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )


def _extract_markdown_heading_names(markdown_content: str) -> set[str]:
    headings: set[str] = set()
    for raw_line in markdown_content.splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line.startswith("#"):
            continue

        heading_text = stripped_line.lstrip("#").strip()
        if not heading_text:
            continue

        headings.add(_normalize_for_quality_checks(heading_text))
    return headings


def _canonical_heading_name(heading: str) -> str:
    normalized_heading = _normalize_for_quality_checks(heading)
    normalized_heading = re.sub(r"^\d+[\).:-]?\s*", "", normalized_heading)
    normalized_heading = re.sub(r"\s*\(etapa\s+\d+\)\s*", "", normalized_heading)
    normalized_heading = normalized_heading.replace("-", " ")
    normalized_heading = re.sub(r"[^a-z0-9 ]+", " ", normalized_heading)
    return re.sub(r"\s+", " ", normalized_heading).strip()


def _extract_urls(content: str) -> list[str]:
    return re.findall(r"https?://[^\s|)\]>]+", content, flags=re.IGNORECASE)


def _extract_competitive_section_text(markdown_content: str) -> str:
    sections: list[str] = []
    capture = False
    for raw_line in markdown_content.splitlines():
        stripped_line = raw_line.strip()
        if stripped_line.startswith("#"):
            heading = _canonical_heading_name(stripped_line.lstrip("#").strip())
            capture = any(
                section in heading
                for section in (
                    "benchmark de concorrentes",
                    "matriz de benchmark competitivo",
                )
            )
            continue

        if capture:
            sections.append(raw_line)

    return "\n".join(sections)


def _is_valid_external_url(url: str) -> bool:
    normalized_url = url.strip().lower().rstrip(".,;")
    if "..." in normalized_url or "…" in normalized_url:
        return False

    return bool(
        re.match(
            r"^https?://[a-z0-9][a-z0-9.-]*\.[a-z]{2,}([/:?#][^\s]*)?$",
            normalized_url,
        )
    )


def _build_researcher_quality_feedback(
    error: ResearcherQualityError,
    *,
    step: MakerStep | None = None,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft | None = None,
) -> str:
    issues = "\n".join(f"- {issue}" for issue in error.issues)
    required_sections = "\n".join(
        f"- {section}" for section in RESEARCHER_REQUIRED_SECTIONS
    )
    rejected_draft_context = ""
    if step is not None and draft is not None:
        rejected_draft_context = (
            f"{_build_rejected_draft_context(step=step, draft=draft)}\n\n"
        )
    return (
        f"{rejected_draft_context}"
        "O validador automatico bloqueou o benchmark por risco de saida "
        "generica/alucinada. Reescreva sem inventar dados, usando somente "
        "fontes rastreaveis ou pendencias explicitas.\n\n"
        f"Problemas encontrados:\n{issues}\n\n"
        "Na proxima resposta, use obrigatoriamente estes headings no Markdown, "
        "sem renomear ou pular secoes:\n"
        f"{required_sections}\n\n"
        "Ignore a estrutura do documento anterior se ela conflitar com o "
        "esqueleto abaixo. O esqueleto e a fonte de verdade para formato nesta "
        "reescrita:\n"
        f"{RESEARCHER_RETRY_SKELETON}\n\n"
        "Obrigatorio na reescrita: declarar dados realmente disponiveis, "
        "separar Extraido do briefing/Fonte externa verificada/Benchmark "
        "interno Healz/Benchmark publico de mercado/Dado pendente, remover "
        "personas ou KPIs sem fonte, incluir Matriz de Benchmark Competitivo "
        "em tabela e Log de Consultas Externas ou Falha de Pesquisa Externa "
        "com consultas reais. Se nao houver acesso a Keyword Planner, Google "
        "Ads, Meta Ads Library ou dados privados de Instagram, registre isso "
        "como pendencia rastreavel e use pesquisa publica verificavel: SERP "
        "comum, sites abertos, Doctoralia, Google Business publico, paginas "
        "institucionais, Instagram publico acessivel e benchmarks publicos "
        "com URL. Se ja houver fonte externa verificada, trate como "
        "Pesquisa externa parcial, nao como falha ainda nao realizada. A secao "
        "Analise de Demanda Google deve conter tabela "
        "com Palavra-chave, Volume e CPC mesmo quando Volume/CPC forem Dado "
        "indisponivel apos pesquisa. A secao Analise Meta deve conter tabela "
        "com Anuncio, Captacao e Autoridade mesmo quando a Meta Ads Library "
        "estiver indisponivel. Toda linha Google Search/SERP com status "
        "Encontrado na fonte precisa de URL completa; sem URL, marque como "
        "Pesquisa nao verificavel, Descartado, Sem URL verificavel, e nao use "
        "como evidencia. Se a coluna URL contiver Nao encontrado nas fontes "
        "consultadas, Dado pendente de validacao externa ou Pesquisa nao "
        "verificavel, o status nao pode ser Encontrado na fonte. Para "
        "ferramentas fechadas indisponiveis, preencha Titulo, URL e Resultado "
        "com texto rastreavel em vez de travessao. Se nao houver dado para uma "
        "secao, preencha a secao "
        "com uma tabela de pendencias, nao com texto generico. Em qualquer "
        "tabela, substitua '-', '—', '–' e celulas vazias por Dado pendente de "
        "validacao externa, Nao encontrado nas fontes consultadas ou Pesquisa "
        "nao verificavel, inclusive em CTA, Funil, Provas, Lacunas, "
        "Oportunidade, Seguidores, Formato, Tema, Data e URL."
    )


def _validate_researcher_mvp_quality(
    markdown_content: str,
    *,
    doctor_name: str | None = None,
) -> None:
    normalized_content = _normalize_for_quality_checks(markdown_content)
    heading_names = _extract_markdown_heading_names(markdown_content)
    external_urls = _extract_urls(markdown_content)
    issues: list[str] = []

    missing_sections = [
        section
        for section in RESEARCHER_REQUIRED_SECTIONS
        if not any(
            _canonical_heading_name(section) in _canonical_heading_name(heading)
            for heading in heading_names
        )
    ]
    if missing_sections:
        issues.append(
            "Secoes obrigatorias ausentes: " + ", ".join(missing_sections) + "."
        )

    generic_hits = [
        pattern
        for pattern in RESEARCHER_GENERIC_PATTERNS
        if pattern in normalized_content
    ]
    if generic_hits:
        issues.append(
            "Sinais de benchmark generico ou dados inventados: "
            + ", ".join(generic_hits)
            + "."
        )

    missing_table_markers: list[str] = []
    for section_name, markers in RESEARCHER_REQUIRED_TABLE_MARKERS:
        if not all(marker in normalized_content for marker in markers):
            missing_table_markers.append(
                f"{section_name} precisa conter campos {', '.join(markers)}"
            )
    if missing_table_markers:
        issues.append(
            "Campos obrigatorios do checklist ausentes: "
            + "; ".join(missing_table_markers)
            + "."
        )

    evidence_hits = sum(
        1
        for term in RESEARCHER_EVIDENCE_TERMS
        if _normalize_for_quality_checks(term) in normalized_content
    )
    if evidence_hits < 3:
        issues.append(
            "Pouca rastreabilidade: use ao menos tres classes/status de "
            "evidencia entre Extraido do briefing, Fonte externa verificada, "
            "Benchmark interno Healz, Benchmark publico de mercado, Dado "
            "pendente de validacao externa, Nao encontrado nas fontes "
            "consultadas ou Dado indisponivel apos pesquisa."
        )

    if "http://" not in normalized_content and "https://" not in normalized_content:
        has_external_failure = (
            "falha de pesquisa externa" in normalized_content
            and "consulta" in normalized_content
        )
        if not has_external_failure:
            issues.append(
                "Nenhuma URL externa encontrada e nenhuma Falha de Pesquisa "
                "Externa com consultas executadas foi declarada."
            )

    invalid_urls = [url for url in external_urls if not _is_valid_external_url(url)]
    if invalid_urls:
        issues.append(
            "URLs externas invalidas ou placeholders: "
            + ", ".join(invalid_urls[:5])
            + ". Use URL completa verificavel ou rebaixe o dado para "
            "Pesquisa nao verificavel/Dado pendente."
        )

    has_external_url = any(_is_valid_external_url(url) for url in external_urls)
    has_unrealized_failure = (
        "falha de pesquisa externa" in normalized_content
        and (
            "ainda nao realizada" in normalized_content
            or "nao realizada" in normalized_content
        )
    )
    if has_external_url and has_unrealized_failure:
        issues.append(
            "Pesquisa externa parcial nao pode ser descrita como Falha de "
            "Pesquisa Externa ainda nao realizada. Use Pesquisa externa "
            "parcial e registre pendencias/falhas restantes."
        )

    if "google business" in normalized_content:
        has_google_business_source = (
            "google business" in normalized_content
            and (
                "extraido do briefing" in normalized_content
                or has_external_url
                or "dado pendente de validacao externa" in normalized_content
            )
        )
        if not has_google_business_source:
            issues.append(
                "Google Business aparece sem fonte clara. Marque como Extraido "
                "do briefing, Fonte externa verificada com URL ou Dado pendente."
            )

    benchmark_section_text = _extract_competitive_section_text(markdown_content)
    normalized_benchmark_section = _normalize_for_quality_checks(
        benchmark_section_text
    )
    normalized_doctor_name = (
        _normalize_for_quality_checks(doctor_name) if doctor_name else ""
    )
    doctor_name_parts = [
        part
        for part in normalized_doctor_name.split()
        if len(part) >= 4 and part not in {"doutor", "doctor"}
    ]
    has_doctor_name_in_competitive_section = bool(
        normalized_doctor_name
        and (
            normalized_doctor_name in normalized_benchmark_section
            or (
                len(doctor_name_parts) >= 2
                and all(
                    part in normalized_benchmark_section
                    for part in doctor_name_parts
                )
            )
        )
    )
    has_self_as_competitor = (
        has_doctor_name_in_competitive_section
        or any(
            phrase in normalized_content
            for phrase in (
                "proprio medico",
                "proprio cliente",
                "nao considerado concorrente",
                "descartado).",
            )
        )
    )
    if has_self_as_competitor:
        issues.append(
            "O proprio medico/cliente nao pode ser listado como concorrente. "
            "Use essa fonte apenas em Dados Extraidos dos Anexos ou Log de "
            "Consultas Externas."
        )

    has_competitive_gap_claim = (
        "lacuna identificada na concorrencia" in normalized_content
        or "oportunidade via seo" in normalized_content
        or "oportunidade via google ads" in normalized_content
    )
    has_verified_competitor = (
        "matriz de benchmark competitivo" in normalized_content
        and "encontrado na fonte" in normalized_content
        and "pesquisa nao verificavel" not in normalized_content
    )
    if has_competitive_gap_claim and not has_verified_competitor:
        issues.append(
            "Lacunas/oportunidades competitivas nao podem ser afirmadas sem "
            "concorrentes verificados com URL. Use 'lacuna de dados "
            "competitivos' ou 'hipotese a validar'."
        )

    if "canais recomendados:" in normalized_content:
        issues.append(
            "Use 'hipotese de canais a validar', nao 'canais recomendados', "
            "quando volume/CPC/concorrentes ainda estiverem pendentes."
        )

    placeholder_table_rows = []
    for raw_line in markdown_content.splitlines():
        normalized_line = _normalize_for_quality_checks(raw_line)
        stripped_line = raw_line.strip()
        if stripped_line.startswith("#"):
            continue

        if "|" not in normalized_line:
            continue
        if set(normalized_line.strip()) <= {"|", "-", ":", " "}:
            continue

        cells = [cell.strip() for cell in normalized_line.strip().strip("|").split("|")]
        if any(cell in {"-", "—", "–", ""} for cell in cells):
            placeholder_table_rows.append(raw_line.strip())

    if placeholder_table_rows:
        issues.append(
            "Tabelas contem placeholders vazios ou travessao: "
            + "; ".join(placeholder_table_rows[:3])
            + ". Use Dado pendente de validacao externa, Nao encontrado nas "
            "fontes consultadas ou Pesquisa nao verificavel."
        )

    if any(metric in normalized_content for metric in ("cpl", "cac", "cpc")):
        has_metric_guardrail = (
            "benchmark interno healz" in normalized_content
            or "benchmark publico de mercado" in normalized_content
            or "dado pendente de validacao externa" in normalized_content
            or "nao encontrado nas fontes consultadas" in normalized_content
        )
        if not has_metric_guardrail:
            issues.append(
                "Metricas como CPL/CAC/CPC aparecem sem status de benchmark "
                "interno, fonte verificada ou pendencia."
            )

    unverifiable_google_lines = []
    undated_google_lines = []
    for raw_line in markdown_content.splitlines():
        normalized_line = _normalize_for_quality_checks(raw_line)
        mentions_google_search = (
            "google search" in normalized_line
            or "serp" in normalized_line
            or "google (web)" in normalized_line
        )
        is_separator = set(normalized_line.strip()) <= {"|", "-", ":", " "}
        if not mentions_google_search or is_separator:
            continue

        looks_like_log_row = "|" in normalized_line
        claims_verified_source = (
            "encontrado na fonte" in normalized_line
            or "fonte externa verificada" in normalized_line
        )
        if not looks_like_log_row and not claims_verified_source:
            continue

        line_urls = _extract_urls(raw_line)
        has_url = any(_is_valid_external_url(url) for url in line_urls)
        has_url_placeholder = any(
            placeholder in normalized_line
            for placeholder in (
                "url do site",
                "url completa",
                "[url",
                "| url |",
                "| urls |",
                "url citada",
            )
        )
        has_relative_date = "| hoje" in normalized_line or "| hoje |" in normalized_line
        has_absolute_date = bool(re.search(r"\d{2}/\d{2}/\d{4}", normalized_line))
        is_suggested_query = (
            "consulta sugerida" in normalized_line
            or "dado pendente de validacao externa" in normalized_line
        )
        is_unverifiable_declared = "pesquisa nao verificavel" in normalized_line
        if looks_like_log_row and not is_suggested_query and not has_absolute_date:
            undated_google_lines.append(raw_line.strip())

        if (
            (not has_url or has_url_placeholder or has_relative_date)
            and not is_suggested_query
            and not is_unverifiable_declared
        ):
            unverifiable_google_lines.append(raw_line.strip())

    if unverifiable_google_lines:
        issues.append(
            "Linhas de Google Search/SERP sem URL verificavel: "
            + "; ".join(unverifiable_google_lines[:3])
            + ". Inclua URL, titulo da pagina e motivo de aproveitamento ou "
            "descarte, ou marque como pesquisa nao verificavel sem sustentar "
            "conclusao."
        )

    if undated_google_lines:
        issues.append(
            "Linhas de Google Search/SERP sem data absoluta: "
            + "; ".join(undated_google_lines[:3])
            + ". Use DD/MM/AAAA para pesquisa executada ou marque como "
            "consulta sugerida/pendente."
        )

    if issues:
        raise ResearcherQualityError(issues)


def _repair_researcher_markdown_content(markdown_content: str) -> str:
    repaired_lines: list[str] = []
    placeholder_status = "Dado pendente de validacao externa"

    for raw_line in markdown_content.splitlines():
        normalized_line = _normalize_for_quality_checks(raw_line)
        stripped_line = raw_line.strip()
        if stripped_line.startswith("#"):
            repaired_lines.append(raw_line)
            continue

        if (
            "|" not in raw_line
            or set(normalized_line.strip()) <= {"|", "-", ":", " "}
        ):
            repaired_lines.append(raw_line)
            continue

        leading_pipe = raw_line.lstrip().startswith("|")
        trailing_pipe = raw_line.rstrip().endswith("|")
        cells = raw_line.strip().strip("|").split("|")
        repaired_cells = []
        for cell in cells:
            stripped_cell = cell.strip()
            if _normalize_for_quality_checks(stripped_cell) == "dado pendente":
                stripped_cell = placeholder_status
            if stripped_cell in {"", "-", "—", "–", "â€”", "â€“"}:
                repaired_cells.append(f" {placeholder_status} ")
            else:
                repaired_cells.append(f" {stripped_cell} ")

        repaired_line = "|".join(repaired_cells)
        if leading_pipe:
            repaired_line = "|" + repaired_line
        if trailing_pipe:
            repaired_line = repaired_line + "|"

        normalized_repaired_line = _normalize_for_quality_checks(repaired_line)
        has_valid_url = any(
            _is_valid_external_url(url) for url in _extract_urls(repaired_line)
        )
        mentions_serp = (
            "google search" in normalized_repaired_line
            or "serp" in normalized_repaired_line
            or "google (web)" in normalized_repaired_line
        )
        if mentions_serp and not has_valid_url:
            repaired_line = repaired_line.replace(
                "Encontrado na fonte", "Pesquisa nao verificavel"
            )

        repaired_lines.append(repaired_line)

    repaired_content = "\n".join(repaired_lines).strip()
    heading_names = _extract_markdown_heading_names(repaired_content)
    missing_sections = [
        section
        for section in RESEARCHER_REQUIRED_SECTIONS
        if not any(
            _canonical_heading_name(section) in _canonical_heading_name(heading)
            for heading in heading_names
        )
    ]

    if missing_sections:
        appended_sections = []
        for section in missing_sections:
            section_body = RESEARCHER_MISSING_SECTION_TEMPLATES[section]
            appended_sections.append(f"## {section}\n{section_body}")
        repaired_content = (
            f"{repaired_content}\n\n"
            "## Complemento automatico de pendencias\n"
            "As secoes abaixo foram completadas com pendencias rastreaveis "
            "porque o agente nao retornou todos os blocos obrigatorios.\n\n"
            + "\n\n".join(appended_sections)
        )

    normalized_content = _normalize_for_quality_checks(repaired_content)
    has_external_url = any(
        _is_valid_external_url(url) for url in _extract_urls(repaired_content)
    )
    has_external_failure = (
        "falha de pesquisa externa" in normalized_content
        and "consulta" in normalized_content
    )
    if not has_external_url and not has_external_failure:
        repaired_content = (
            f"{repaired_content}\n\n"
            "## Falha de Pesquisa Externa\n"
            "| Consulta executada | Fonte/ferramenta | Data | Titulo da pagina | "
            "URL | Resultado principal | Aproveitamento/descarte | Motivo | "
            "Status |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| Consulta sugerida por especialidade + cidade | Google Search | "
            "Dado pendente de validacao externa | Dado pendente de validacao "
            "externa | Dado pendente de validacao externa | Dado pendente de "
            "validacao externa | Descartado | Sem URL verificavel no documento "
            "gerado | Pesquisa nao verificavel |"
        )

    return repaired_content


def _build_human_review_escalation_feedback(
    review: ReviewerDecision,
    *,
    step: MakerStep | None = None,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft | None = None,
) -> str:
    rewrite_feedback = _build_rewrite_feedback(review, step=step, draft=draft)
    return (
        "O checker CFM automatico nao aprovou esta versao dentro do limite "
        "de reescritas, entao o benchmark foi encaminhado para revisao humana "
        "em vez de bloquear o MVP.\n\n"
        f"{rewrite_feedback}"
    )


def _validate_step_output(
    *,
    step: MakerStep,
    draft: GeneratedDocumentDraft | GeneratedHtmlDocumentDraft,
    required_css_ids: list[str],
    onboarding: Onboarding | None = None,
) -> None:
    if step.step_name == "researcher" and step.output_kind == "markdown":
        if isinstance(draft, GeneratedDocumentDraft):
            draft.markdown_content = _repair_researcher_markdown_content(
                draft.markdown_content
            )
        _validate_researcher_mvp_quality(
            _extract_document_content(step=step, draft=draft),
            doctor_name=onboarding.doctor_name if onboarding else None,
        )
        return

    if step.output_kind != "html":
        return

    validate_generated_html(
        html_content=_extract_document_content(step=step, draft=draft),
        required_css_ids=required_css_ids,
    )


async def _record_maker_progress(
    *,
    pipeline_service: PipelineService,
    db: AsyncSession,
    onboarding_id: int,
    step: MakerStep,
    result: AgentRunResult,
    title: str,
    review_round: int,
) -> None:
    await pipeline_service.record_progress(
        db=db,
        onboarding_id=onboarding_id,
        step_name=step.step_name,
        trigger="agent_step_completed",
        to_status="RUNNING",
        extra_payload={
            "attempt_count": result.attempt_count,
            "agent_name": result.agent_name,
            "model": result.model,
            "document_kind": step.document_kind,
            "document_title": title,
            "review_round": review_round,
        },
    )


async def _record_maker_started(
    *,
    pipeline_service: PipelineService,
    db: AsyncSession,
    onboarding_id: int,
    step: MakerStep,
    review_round: int,
    model: str,
) -> None:
    await pipeline_service.record_progress(
        db=db,
        onboarding_id=onboarding_id,
        step_name=step.step_name,
        trigger="agent_step_started",
        to_status="RUNNING",
        extra_payload={
            "agent_name": step.agent_name,
            "model": model,
            "document_kind": step.document_kind,
            "review_round": review_round,
        },
    )


async def _record_reviewer_progress(
    *,
    pipeline_service: PipelineService,
    db: AsyncSession,
    onboarding_id: int,
    step: MakerStep,
    result: AgentRunResult,
    review: ReviewerDecision,
    review_round: int,
) -> None:
    await pipeline_service.record_progress(
        db=db,
        onboarding_id=onboarding_id,
        step_name=f"{step.step_name}_review",
        trigger=("review_step_approved" if review.approved else "review_step_rejected"),
        to_status=(PIPELINE_AWAITING_REVIEW_STATUS if review.approved else "RUNNING"),
        extra_payload={
            "attempt_count": result.attempt_count,
            "agent_name": result.agent_name,
            "model": result.model,
            "document_kind": step.document_kind,
            "approved": review.approved,
            "feedback_summary": review.feedback_summary,
            "violations": review.violations,
            "rewrite_instructions": review.rewrite_instructions,
            "review_round": review_round,
            "reviewed_agent": step.agent_name,
        },
    )


async def _record_reviewer_started(
    *,
    pipeline_service: PipelineService,
    db: AsyncSession,
    onboarding_id: int,
    step: MakerStep,
    review_round: int,
    model: str,
) -> None:
    await pipeline_service.record_progress(
        db=db,
        onboarding_id=onboarding_id,
        step_name=f"{step.step_name}_review",
        trigger="review_step_started",
        to_status="RUNNING",
        extra_payload={
            "agent_name": REVIEWER_AGENT_NAME,
            "model": model,
            "document_kind": step.document_kind,
            "review_round": review_round,
            "reviewed_agent": step.agent_name,
        },
    )


async def bootstrap_pipeline(
    onboarding_id: int,
    *,
    start_from_step: str | None = None,
    human_feedback: str | None = None,
    session_factory: Callable[
        [],
        AbstractAsyncContextManager[AsyncSession],
    ] = AsyncSessionLocal,
    pipeline_service_factory: Callable[[], PipelineService] = PipelineService,
    generated_document_service_factory: Callable[
        [],
        GeneratedDocumentService,
    ] = GeneratedDocumentService,
    asset_service_factory: Callable[[], AssetService] = AssetService,
    runner: AgentRunner | None = None,
) -> None:
    """Execute the Maker -> Checker steps of the pipeline in background."""
    agent_runner = runner or AgentRunner()
    pipeline_service = pipeline_service_factory()
    generated_document_service = generated_document_service_factory()
    asset_service = asset_service_factory()

    async with session_factory() as db:
        onboarding = await _load_onboarding(db=db, onboarding_id=onboarding_id)
        if onboarding is None:
            logger.warning(
                "Pipeline bootstrap aborted because onboarding was not found.",
                extra={"onboarding_id": onboarding_id},
            )
            return

        current_step = MAKER_STEPS[0]
        current_step_name = current_step.step_name
        current_agent_name = current_step.agent_name

        try:
            current_step = _resolve_pipeline_step(start_from_step)
        except ValueError as error:
            await pipeline_service.fail_pipeline(
                db=db,
                onboarding_id=onboarding_id,
                step_name=current_step_name,
                trigger="pipeline_step_invalid",
                error_code="PIPELINE_STEP_INVALID",
                error_message=str(error),
                attempt_count=1,
                agent_name=current_agent_name,
                model=_resolve_runner_model(agent_runner),
            )
            return

        current_step_name = current_step.step_name
        current_agent_name = current_step.agent_name

        try:
            transcription_context = await _build_transcription_context(
                db=db,
                onboarding_id=onboarding_id,
                asset_service=asset_service,
            )
            required_css_ids: list[str] = []
            approved_documents = await generated_document_service.list_documents(
                db=db,
                onboarding_id=onboarding_id,
                review_status=DOCUMENT_REVIEW_STATUS_APPROVED,
            )
            previous_documents = _build_previous_documents_for_step(
                step=current_step,
                approved_documents=approved_documents,
            )
            rewrite_feedback: str | None = None

            for review_round in range(1, REVIEWER_MAX_REWRITE_ATTEMPTS + 1):
                current_step_name = current_step.step_name
                current_agent_name = current_step.agent_name
                await _record_maker_started(
                    pipeline_service=pipeline_service,
                    db=db,
                    onboarding_id=onboarding_id,
                    step=current_step,
                    review_round=review_round,
                    model=_resolve_runner_model(agent_runner),
                )
                run_result = await agent_runner.run(
                    agent_name=current_step.agent_name,
                    step_name=current_step.step_name,
                    system_prompt=current_step.prompt_builder(),
                    user_prompt=_build_maker_user_prompt(
                        step=current_step,
                        onboarding=onboarding,
                        transcription_context=transcription_context,
                        previous_documents=previous_documents,
                        review_feedback=rewrite_feedback,
                        human_feedback=human_feedback,
                        step_specific_context=None,
                    ),
                    response_format=_build_step_response_format(current_step),
                    enable_web_search=current_step.step_name == "researcher",
                )
                generated_draft = _parse_step_output(
                    step=current_step,
                    raw_content=run_result.content,
                )
                await _record_maker_progress(
                    pipeline_service=pipeline_service,
                    db=db,
                    onboarding_id=onboarding_id,
                    step=current_step,
                    result=run_result,
                    title=generated_draft.title,
                    review_round=review_round,
                )
                try:
                    _validate_step_output(
                        step=current_step,
                        draft=generated_draft,
                        required_css_ids=required_css_ids,
                        onboarding=onboarding,
                    )
                except ResearcherQualityError as error:
                    if review_round == REVIEWER_MAX_REWRITE_ATTEMPTS:
                        quality_feedback = _build_researcher_quality_feedback(
                            error,
                            step=current_step,
                            draft=generated_draft,
                        )
                        await pipeline_service.fail_pipeline(
                            db=db,
                            onboarding_id=onboarding_id,
                            step_name=current_step.step_name,
                            trigger="researcher_quality_validation_failed",
                            error_code="RESEARCHER_BENCHMARK_GENERIC",
                            error_message=(
                                "O benchmark gerado parece generico ou sem "
                                "rastreabilidade suficiente. Ajuste as fontes "
                                "do onboarding ou tente novamente."
                            ),
                            attempt_count=review_round,
                            agent_name=current_step.agent_name,
                            model=run_result.model,
                            extra_payload={
                                "issues": error.issues,
                                "quality_feedback": quality_feedback,
                                "document_title": generated_draft.title,
                            },
                        )
                        return

                    rewrite_feedback = _build_researcher_quality_feedback(
                        error,
                        step=current_step,
                        draft=generated_draft,
                    )
                    await pipeline_service.record_progress(
                        db=db,
                        onboarding_id=onboarding_id,
                        step_name=current_step.step_name,
                        trigger="researcher_quality_validation_rejected",
                        to_status="RUNNING",
                        extra_payload={
                            "attempt_count": run_result.attempt_count,
                            "agent_name": current_step.agent_name,
                            "model": run_result.model,
                            "document_kind": current_step.document_kind,
                            "document_title": generated_draft.title,
                            "review_round": review_round,
                            "issues": error.issues,
                        },
                    )
                    continue

                current_step_name = f"{current_step.step_name}_review"
                current_agent_name = REVIEWER_AGENT_NAME
                await _record_reviewer_started(
                    pipeline_service=pipeline_service,
                    db=db,
                    onboarding_id=onboarding_id,
                    step=current_step,
                    review_round=review_round,
                    model=_resolve_runner_model(agent_runner),
                )
                review_result = await agent_runner.run(
                    agent_name=REVIEWER_AGENT_NAME,
                    step_name=current_step_name,
                    system_prompt=build_reviewer_system_prompt(),
                    user_prompt=_build_reviewer_user_prompt(
                        onboarding=onboarding,
                        step=current_step,
                        draft=generated_draft,
                    ),
                    response_format=_build_reviewer_response_format(),
                )
                reviewer_decision = ReviewerDecision.model_validate_json(
                    review_result.content
                )
                if reviewer_decision.approved:
                    await generated_document_service.save_document(
                        db=db,
                        onboarding_id=onboarding_id,
                        step_name=current_step.step_name,
                        agent_name=current_step.agent_name,
                        document_kind=current_step.document_kind,
                        title=generated_draft.title,
                        markdown_content=_extract_document_content(
                            step=current_step,
                            draft=generated_draft,
                        ),
                        review_status=DOCUMENT_REVIEW_STATUS_AWAITING,
                        review_feedback=None,
                        reviewed_at=None,
                    )
                    await _record_reviewer_progress(
                        pipeline_service=pipeline_service,
                        db=db,
                        onboarding_id=onboarding_id,
                        step=current_step,
                        result=review_result,
                        review=reviewer_decision,
                        review_round=review_round,
                    )
                    return

                await _record_reviewer_progress(
                    pipeline_service=pipeline_service,
                    db=db,
                    onboarding_id=onboarding_id,
                    step=current_step,
                    result=review_result,
                    review=reviewer_decision,
                    review_round=review_round,
                )

                if review_round == REVIEWER_MAX_REWRITE_ATTEMPTS:
                    await generated_document_service.save_document(
                        db=db,
                        onboarding_id=onboarding_id,
                        step_name=current_step.step_name,
                        agent_name=current_step.agent_name,
                        document_kind=current_step.document_kind,
                        title=generated_draft.title,
                        markdown_content=_extract_document_content(
                            step=current_step,
                            draft=generated_draft,
                        ),
                        review_status=DOCUMENT_REVIEW_STATUS_AWAITING,
                        review_feedback=_build_human_review_escalation_feedback(
                            reviewer_decision,
                            step=current_step,
                            draft=generated_draft,
                        ),
                        reviewed_at=None,
                    )
                    await pipeline_service.record_progress(
                        db=db,
                        onboarding_id=onboarding_id,
                        step_name=current_step_name,
                        trigger="review_step_escalated_to_human",
                        to_status=PIPELINE_AWAITING_REVIEW_STATUS,
                        extra_payload={
                            "attempt_count": review_result.attempt_count,
                            "agent_name": REVIEWER_AGENT_NAME,
                            "model": review_result.model,
                            "document_kind": current_step.document_kind,
                            "review_round": review_round,
                            "reviewed_agent": current_step.agent_name,
                            "feedback_summary": reviewer_decision.feedback_summary,
                            "violations": reviewer_decision.violations,
                            "rewrite_instructions": (
                                reviewer_decision.rewrite_instructions
                            ),
                        },
                    )
                    return

                rewrite_feedback = _build_rewrite_feedback(
                    reviewer_decision,
                    step=current_step,
                    draft=generated_draft,
                )
        except HTMLValidationError as error:
            await pipeline_service.fail_pipeline(
                db=db,
                onboarding_id=onboarding_id,
                step_name=current_step_name,
                trigger="html_validation_failed",
                error_code=error.error_code,
                error_message=error.message,
                attempt_count=1,
                agent_name=current_agent_name,
                model=_resolve_runner_model(agent_runner),
            )
        except AgentRunnerError as error:
            await pipeline_service.fail_pipeline(
                db=db,
                onboarding_id=onboarding_id,
                step_name=current_step_name,
                trigger="agent_runner_failed",
                error_code=error.error_code,
                error_message=error.message,
                attempt_count=error.attempt_count,
                agent_name=error.agent_name,
                model=error.model,
            )
        except ValidationError:
            error_code = (
                "REVIEWER_OUTPUT_INVALID"
                if current_agent_name == REVIEWER_AGENT_NAME
                else "AGENT_OUTPUT_INVALID"
            )
            error_message = (
                "O checker CFM retornou uma resposta invalida para continuar o "
                "pipeline."
                if current_agent_name == REVIEWER_AGENT_NAME
                else "O agente retornou um documento invalido para continuar "
                "o pipeline."
            )
            await pipeline_service.fail_pipeline(
                db=db,
                onboarding_id=onboarding_id,
                step_name=current_step_name,
                trigger="agent_output_invalid",
                error_code=error_code,
                error_message=error_message,
                attempt_count=1,
                agent_name=current_agent_name,
                model=_resolve_runner_model(agent_runner),
            )
        except Exception:
            logger.exception(
                "Unexpected failure while executing maker steps.",
                extra={
                    "onboarding_id": onboarding_id,
                    "step_name": current_step_name,
                },
            )
            await pipeline_service.fail_pipeline(
                db=db,
                onboarding_id=onboarding_id,
                step_name=current_step_name,
                trigger="agent_runner_failed",
                error_code="AGENT_RUNNER_FAILED",
                error_message="O pipeline falhou ao executar a cadeia de agentes.",
                attempt_count=1,
                agent_name=current_agent_name,
                model=_resolve_runner_model(agent_runner),
            )
