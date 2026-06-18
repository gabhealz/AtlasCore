import json
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import (
    bootstrap_pipeline,
    get_next_step_name,
    get_step_output_kind,
)
from app.api import deps
from app.services.usage_service import summarize_onboarding_cost
from app.models.onboarding import Onboarding
from app.models.uploaded_asset import UploadedAsset
from app.models.user import User
from app.schemas.generated_document import (
    GeneratedDeliverableEnvelope,
    GeneratedDeliverableListEnvelope,
    GeneratedDeliverableResponse,
)
from app.schemas.human_review import (
    HumanReviewActionEnvelope,
    HumanReviewActionResponse,
    HumanReviewApproveRequest,
    HumanReviewDocumentEnvelope,
    HumanReviewDocumentResponse,
    HumanReviewRejectRequest,
)
from app.schemas.onboarding import (
    OnboardingCreate,
    OnboardingDetailEnvelope,
    OnboardingListResponse,
)
from app.schemas.pipeline import PipelineStartEnvelope
from app.services.generated_document_service import (
    DOCUMENT_REVIEW_STATUS_APPROVED,
    DOCUMENT_REVIEW_STATUS_REJECTED,
    GeneratedDocumentService,
)
from app.services.pipeline_service import PipelineService

router = APIRouter()

TEXT_DELIVERABLE_ORDER = [
    "research_report",
]
LANDING_PAGE_HTML_KIND = "landing_page_html"

# Reviewers can read, Operators can read, Admins can read
allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])

# Only Operators and Admins can write
allow_write = deps.RoleChecker(["admin", "operator"])

PipelineStarter = Callable[..., Awaitable[None] | None]


def get_pipeline_service() -> PipelineService:
    return PipelineService()


def get_generated_document_service() -> GeneratedDocumentService:
    return GeneratedDocumentService()


def get_pipeline_starter() -> PipelineStarter:
    return bootstrap_pipeline


def _raise_api_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
    extra_detail: dict[str, str] | None = None,
) -> None:
    detail: dict[str, str] = {"error_code": error_code, "message": message}
    if extra_detail:
        detail.update(extra_detail)

    raise HTTPException(status_code=status_code, detail=detail)


async def _get_onboarding_or_404(
    *,
    db: AsyncSession,
    onboarding_id: int,
    for_update: bool = False,
) -> Onboarding:
    query = select(Onboarding).where(Onboarding.id == onboarding_id)
    if for_update:
        query = query.with_for_update()

    result = await db.execute(query)
    onboarding = result.scalars().first()
    if onboarding is None:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ONBOARDING_NOT_FOUND",
            message="Onboarding nao encontrado.",
        )

    return onboarding


async def _ensure_pipeline_inputs_ready(
    db: AsyncSession,
    *,
    onboarding_id: int,
) -> None:
    assets_result = await db.execute(
        select(UploadedAsset).where(UploadedAsset.onboarding_id == onboarding_id)
    )
    assets = assets_result.scalars().all()
    has_document = any(asset.asset_kind == "transcription" for asset in assets)

    missing_items = []
    if not has_document:
        missing_items.append("ao menos 1 documento base ou transcricao")

    if missing_items:
        _raise_api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PIPELINE_INPUTS_INCOMPLETE",
            message=(
                "Complete os insumos antes de iniciar a esteira de IA: "
                + "; ".join(missing_items)
                + "."
            ),
        )


def _parse_search_sources(raw: str | None) -> list[dict]:
    """Decodifica o JSON de fontes reais da pesquisa, tolerando dados invalidos."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _serialize_review_document(
    document,
) -> HumanReviewDocumentResponse:
    return HumanReviewDocumentResponse(
        id=document.id,
        onboarding_id=document.onboarding_id,
        step_name=document.step_name,
        agent_name=document.agent_name,
        document_kind=document.document_kind,
        title=document.title,
        content=document.markdown_content,
        content_format=get_step_output_kind(document.step_name),
        review_status=document.review_status,
        review_feedback=document.review_feedback,
        reviewed_at=document.reviewed_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
        search_sources=_parse_search_sources(
            getattr(document, "search_sources", None)
        ),
    )


@router.get("/{onboarding_id}/cost")
async def get_onboarding_cost(
    onboarding_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    """Custo operacional (LLM + web search) acumulado deste onboarding."""
    await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    summary = await summarize_onboarding_cost(db, onboarding_id)
    return {"data": summary}


def _validate_human_review_state(onboarding: Onboarding) -> None:
    if onboarding.status != "AWAITING_REVIEW":
        _raise_api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_PIPELINE_STATE",
            message="Este onboarding nao esta aguardando revisao humana.",
            extra_detail={"current_status": onboarding.status},
        )


def _validate_delivery_state(onboarding: Onboarding) -> None:
    if onboarding.status != "APPROVED":
        _raise_api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_PIPELINE_STATE",
            message=(
                "Os entregaveis finais so ficam disponiveis apos a aprovacao final."
            ),
            extra_detail={"current_status": onboarding.status},
        )


def _serialize_text_deliverable(document) -> GeneratedDeliverableResponse:
    return GeneratedDeliverableResponse(
        id=document.id,
        onboarding_id=document.onboarding_id,
        step_name=document.step_name,
        agent_name=document.agent_name,
        document_kind=document.document_kind,
        title=document.title,
        content=document.markdown_content,
        content_format="markdown",
        review_status=document.review_status,
        review_feedback=document.review_feedback,
        reviewed_at=document.reviewed_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _serialize_html_deliverable(document) -> GeneratedDeliverableResponse:
    return GeneratedDeliverableResponse(
        id=document.id,
        onboarding_id=document.onboarding_id,
        step_name=document.step_name,
        agent_name=document.agent_name,
        document_kind=document.document_kind,
        title=document.title,
        content=document.markdown_content,
        content_format="html",
        review_status=document.review_status,
        review_feedback=document.review_feedback,
        reviewed_at=document.reviewed_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


async def _apply_human_review_transition(
    *,
    db: AsyncSession,
    onboarding_id: int,
    reviewed_document,
    pipeline_service: PipelineService,
    trigger: str,
    to_status: str,
    extra_payload: dict[str, str | None],
) -> dict[str, str]:
    try:
        payload = await pipeline_service.record_progress(
            db=db,
            onboarding_id=onboarding_id,
            step_name=reviewed_document.step_name,
            trigger=trigger,
            to_status=to_status,
            extra_payload=extra_payload,
            auto_commit=False,
            publish=False,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await pipeline_service.publish_state_change(
        onboarding_id=onboarding_id,
        payload=payload,
    )
    return payload


@router.get("", response_model=OnboardingListResponse)
async def get_onboardings(
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(select(Onboarding).order_by(Onboarding.created_at.desc()))
    onboardings = result.scalars().all()
    return {"data": onboardings}


@router.get("/{onboarding_id}", response_model=OnboardingDetailEnvelope)
async def get_onboarding(
    onboarding_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    onboarding = await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    return {"data": onboarding}

@router.post(
    "",
    response_model=OnboardingDetailEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_onboarding(
    onboarding_in: OnboardingCreate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    onboarding = Onboarding(
        **onboarding_in.model_dump(),
        status="PENDING",
    )
    db.add(onboarding)
    await db.commit()
    await db.refresh(onboarding)
    return {"data": onboarding}


@router.post(
    "/{onboarding_id}/start",
    response_model=PipelineStartEnvelope,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_onboarding_pipeline(
    onboarding_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    pipeline_starter: PipelineStarter = Depends(get_pipeline_starter),
):
    await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    await _ensure_pipeline_inputs_ready(db=db, onboarding_id=onboarding_id)
    start_response = await pipeline_service.start_pipeline(
        db=db,
        onboarding_id=onboarding_id,
    )
    background_tasks.add_task(pipeline_starter, onboarding_id)
    return {"data": start_response}


@router.get(
    "/{onboarding_id}/review",
    response_model=HumanReviewDocumentEnvelope,
)
async def get_onboarding_pending_review(
    onboarding_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
):
    await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    pending_document = await generated_document_service.get_pending_document(
        db=db,
        onboarding_id=onboarding_id,
    )
    if pending_document is None:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PENDING_REVIEW_NOT_FOUND",
            message="Nenhum documento aguardando revisao humana para este onboarding.",
        )

    return {"data": _serialize_review_document(pending_document)}


@router.get(
    "/{onboarding_id}/deliverables",
    response_model=GeneratedDeliverableListEnvelope,
)
async def get_onboarding_deliverables(
    onboarding_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
):
    del current_user
    onboarding = await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    _validate_delivery_state(onboarding)

    approved_documents = await generated_document_service.list_documents(
        db=db,
        onboarding_id=onboarding_id,
        review_status=DOCUMENT_REVIEW_STATUS_APPROVED,
    )
    text_deliverables = {
        document.document_kind: document
        for document in approved_documents
        if document.document_kind in TEXT_DELIVERABLE_ORDER
    }
    ordered_deliverables = [
        text_deliverables[document_kind]
        for document_kind in TEXT_DELIVERABLE_ORDER
        if document_kind in text_deliverables
    ]
    if not ordered_deliverables:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="DELIVERABLES_NOT_FOUND",
            message=(
                "Nenhum entregavel final de texto foi encontrado para este "
                "onboarding."
            ),
        )

    return {
        "data": [
            _serialize_text_deliverable(document)
            for document in ordered_deliverables
        ]
    }


@router.get(
    "/{onboarding_id}/landing-page-html",
    response_model=GeneratedDeliverableEnvelope,
)
async def get_onboarding_landing_page_html(
    onboarding_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
):
    del current_user
    onboarding = await _get_onboarding_or_404(db=db, onboarding_id=onboarding_id)
    _validate_delivery_state(onboarding)

    approved_documents = await generated_document_service.list_documents(
        db=db,
        onboarding_id=onboarding_id,
        review_status=DOCUMENT_REVIEW_STATUS_APPROVED,
    )
    landing_page_html = next(
        (
            document
            for document in approved_documents
            if document.document_kind == LANDING_PAGE_HTML_KIND
        ),
        None,
    )
    if landing_page_html is None:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LANDING_PAGE_HTML_NOT_FOUND",
            message=(
                "Nenhum HTML final aprovado foi encontrado para este onboarding."
            ),
        )

    return {"data": _serialize_html_deliverable(landing_page_html)}


@router.post(
    "/{onboarding_id}/review/approve",
    response_model=HumanReviewActionEnvelope,
)
async def approve_onboarding_review(
    onboarding_id: int,
    review_in: HumanReviewApproveRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
    pipeline_starter: PipelineStarter = Depends(get_pipeline_starter),
):
    onboarding = await _get_onboarding_or_404(
        db=db,
        onboarding_id=onboarding_id,
        for_update=True,
    )
    _validate_human_review_state(onboarding)

    pending_document = await generated_document_service.get_pending_document(
        db=db,
        onboarding_id=onboarding_id,
        for_update=True,
    )
    if pending_document is None:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PENDING_REVIEW_NOT_FOUND",
            message="Nenhum documento pendente foi encontrado para aprovacao.",
        )

    approved_document = await generated_document_service.apply_human_review(
        db=db,
        document=pending_document,
        review_status=DOCUMENT_REVIEW_STATUS_APPROVED,
        title=review_in.title,
        markdown_content=review_in.content,
        review_feedback=None,
        auto_commit=False,
    )
    next_step_name = get_next_step_name(approved_document.step_name)

    if next_step_name is None:
        final_status = "PENDING_CLIENT_CREATION"
        await _apply_human_review_transition(
            db=db,
            onboarding_id=onboarding_id,
            reviewed_document=approved_document,
            pipeline_service=pipeline_service,
            trigger="human_review_approved",
            to_status=final_status,
            extra_payload={
                "document_kind": approved_document.document_kind,
                "document_title": approved_document.title,
            },
        )
        # Pré-cria o cadastro do cliente (rascunho) automaticamente ao finalizar.
        await _ensure_draft_client(db=db, onboarding_id=onboarding_id)
        return {
            "data": HumanReviewActionResponse(
                onboarding_id=onboarding_id,
                status=final_status,
                next_step_name=None,
            )
        }

    await _apply_human_review_transition(
        db=db,
        onboarding_id=onboarding_id,
        reviewed_document=approved_document,
        pipeline_service=pipeline_service,
        trigger="human_review_approved",
        to_status="RUNNING",
        extra_payload={
            "document_kind": approved_document.document_kind,
            "document_title": approved_document.title,
            "next_step_name": next_step_name,
        },
    )
    background_tasks.add_task(
        pipeline_starter,
        onboarding_id,
        start_from_step=next_step_name,
    )
    return {
        "data": HumanReviewActionResponse(
            onboarding_id=onboarding_id,
            status="RUNNING",
            next_step_name=next_step_name,
        )
    }


@router.post(
    "/{onboarding_id}/review/reject",
    response_model=HumanReviewActionEnvelope,
)
async def reject_onboarding_review(
    onboarding_id: int,
    review_in: HumanReviewRejectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
    pipeline_starter: PipelineStarter = Depends(get_pipeline_starter),
):
    onboarding = await _get_onboarding_or_404(
        db=db,
        onboarding_id=onboarding_id,
        for_update=True,
    )
    _validate_human_review_state(onboarding)

    pending_document = await generated_document_service.get_pending_document(
        db=db,
        onboarding_id=onboarding_id,
        for_update=True,
    )
    if pending_document is None:
        _raise_api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PENDING_REVIEW_NOT_FOUND",
            message="Nenhum documento pendente foi encontrado para recusa.",
        )

    rejected_document = await generated_document_service.apply_human_review(
        db=db,
        document=pending_document,
        review_status=DOCUMENT_REVIEW_STATUS_REJECTED,
        review_feedback=review_in.feedback,
        auto_commit=False,
    )
    await _apply_human_review_transition(
        db=db,
        onboarding_id=onboarding_id,
        reviewed_document=rejected_document,
        pipeline_service=pipeline_service,
        trigger="human_review_rejected",
        to_status="RUNNING",
        extra_payload={
            "document_kind": rejected_document.document_kind,
            "review_feedback": review_in.feedback,
            "next_step_name": rejected_document.step_name,
        },
    )
    background_tasks.add_task(
        pipeline_starter,
        onboarding_id,
        start_from_step=rejected_document.step_name,
        human_feedback=review_in.feedback,
    )
    return {
        "data": HumanReviewActionResponse(
            onboarding_id=onboarding_id,
            status="RUNNING",
            next_step_name=rejected_document.step_name,
        )
    }


from app.schemas.onboarding import OnboardingActivateClient
from app.models.client import Client


async def _ensure_draft_client(db: AsyncSession, onboarding_id: int) -> None:
    """Pré-cria um cliente em RASCUNHO ao finalizar o onboarding (idempotente).

    Preenche o que já temos do onboarding (nome do médico, especialidade). O
    usuário depois completa os dados (fee, cidade, etc.) e liga as integrações.
    """
    onboarding = (
        await db.execute(select(Onboarding).where(Onboarding.id == onboarding_id))
    ).scalars().first()
    if onboarding is None:
        return
    existing = await db.execute(
        select(Client).where(Client.onboarding_id == onboarding_id)
    )
    if existing.scalars().first() is not None:
        return
    db.add(Client(
        name=onboarding.doctor_name,
        specialty=onboarding.specialty,
        monthly_fee=0,
        onboarding_id=onboarding.id,
        is_active=True,
        is_draft=True,
    ))
    await db.commit()


@router.post(
    "/{onboarding_id}/activate_client",
    status_code=status.HTTP_200_OK,
)
async def activate_client_from_onboarding(
    onboarding_id: int,
    activation_data: OnboardingActivateClient,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    onboarding = await _get_onboarding_or_404(
        db=db,
        onboarding_id=onboarding_id,
        for_update=True,
    )

    if onboarding.status != "PENDING_CLIENT_CREATION":
        _raise_api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_ONBOARDING_STATE",
            message="O onboarding não está aguardando a criação do cliente.",
            extra_detail={"current_status": onboarding.status},
        )

    existing = await db.execute(
        select(Client).where(Client.onboarding_id == onboarding_id)
    )
    client = existing.scalars().first()

    if client is not None:
        # Completa o rascunho criado automaticamente.
        client.email = activation_data.email
        client.phone = activation_data.phone
        client.city = activation_data.city
        client.state = activation_data.state
        client.monthly_fee = activation_data.monthly_fee
        client.is_draft = False
        client.is_active = True
    else:
        client = Client(
            name=onboarding.doctor_name,
            specialty=onboarding.specialty,
            email=activation_data.email,
            phone=activation_data.phone,
            city=activation_data.city,
            state=activation_data.state,
            monthly_fee=activation_data.monthly_fee,
            onboarding_id=onboarding.id,
            is_active=True,
            is_draft=False,
        )
        db.add(client)

    onboarding.status = "COMPLETED"
    await db.commit()
    await db.refresh(client)

    return {"status": "success", "client_id": client.id}
