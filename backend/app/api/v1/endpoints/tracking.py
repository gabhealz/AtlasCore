import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.cta_button import CTAButton
from app.models.onboarding import Onboarding
from app.schemas.tracking import (
    CTAButtonCreate,
    CTAButtonEnvelope,
    CTAButtonListEnvelope,
    TrackingSheetEnvelope,
)
from app.services.generated_document_service import (
    DOCUMENT_REVIEW_STATUS_APPROVED,
    GeneratedDocumentService,
)
from app.services.tracking_service import (
    LANDING_PAGE_HTML_KIND,
    TrackingService,
    TrackingSheetValidationError,
)

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])
allow_write = deps.RoleChecker(["admin", "operator"])

CSS_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


def get_tracking_service() -> TrackingService:
    return TrackingService()


def get_generated_document_service() -> GeneratedDocumentService:
    return GeneratedDocumentService()


def _http_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error_code": error_code, "message": message},
    )


def _validate_css_id(css_id: str) -> str:
    normalized_css_id = css_id.strip().lower()
    if not CSS_ID_PATTERN.fullmatch(normalized_css_id):
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_CSS_ID",
            message=(
                "ID CSS invalido. Use letras minusculas, numeros, '-' ou '_' "
                "e inicie com letra."
            ),
        )

    return normalized_css_id


def _validate_tracking_sheet_state(onboarding: Onboarding) -> None:
    if onboarding.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_PIPELINE_STATE",
                "message": (
                    "A Tracking Sheet final so fica disponivel apos a aprovacao "
                    "final."
                ),
                "current_status": onboarding.status,
            },
        )


async def _get_onboarding_or_404(db: AsyncSession, onboarding_id: int) -> Onboarding:
    result = await db.execute(select(Onboarding).where(Onboarding.id == onboarding_id))
    onboarding = result.scalars().first()
    if onboarding is None:
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ONBOARDING_NOT_FOUND",
            message="Onboarding nao encontrado.",
        )

    return onboarding


async def _ensure_css_id_is_unique(
    db: AsyncSession,
    *,
    onboarding_id: int,
    css_id: str,
) -> None:
    result = await db.execute(
        select(CTAButton).where(
            CTAButton.onboarding_id == onboarding_id,
            CTAButton.css_id == css_id,
        )
    )
    existing_button = result.scalars().first()
    if existing_button is not None:
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DUPLICATE_CSS_ID",
            message="Ja existe um botao CTA com este ID CSS neste onboarding.",
        )


async def _list_cta_buttons(
    db: AsyncSession,
    *,
    onboarding_id: int,
) -> list[CTAButton]:
    result = await db.execute(
        select(CTAButton)
        .where(CTAButton.onboarding_id == onboarding_id)
        .order_by(CTAButton.created_at.asc(), CTAButton.id.asc())
    )
    return list(result.scalars().all())


@router.get(
    "/{onboarding_id}/cta_buttons",
    response_model=CTAButtonListEnvelope,
)
async def get_cta_buttons(
    onboarding_id: int,
    _current_user=Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    await _get_onboarding_or_404(db, onboarding_id)
    cta_buttons = await _list_cta_buttons(db, onboarding_id=onboarding_id)
    return {"data": cta_buttons}


@router.get(
    "/{onboarding_id}/sheet",
    response_model=TrackingSheetEnvelope,
)
async def get_tracking_sheet(
    onboarding_id: int,
    _current_user=Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
    tracking_service: TrackingService = Depends(get_tracking_service),
    generated_document_service: GeneratedDocumentService = Depends(
        get_generated_document_service
    ),
):
    onboarding = await _get_onboarding_or_404(db, onboarding_id)
    _validate_tracking_sheet_state(onboarding)

    cta_buttons = await _list_cta_buttons(db, onboarding_id=onboarding_id)
    if not cta_buttons:
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TRACKING_SHEET_NOT_FOUND",
            message=(
                "Nenhum botao CTA cadastrado foi encontrado para montar a "
                "Tracking Sheet deste onboarding."
            ),
        )

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
        _http_error(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="LANDING_PAGE_HTML_NOT_FOUND",
            message=(
                "Nao foi possivel montar a Tracking Sheet porque o HTML final "
                "aprovado nao foi encontrado."
            ),
        )

    try:
        tracking_service.validate_html_matches_cta_matrix(
            landing_page_html=landing_page_html.markdown_content,
            cta_buttons=cta_buttons,
        )
    except TrackingSheetValidationError as error:
        _http_error(
            status_code=status.HTTP_409_CONFLICT,
            error_code=error.error_code,
            message=error.message,
        )

    return {"data": tracking_service.build_tracking_sheet_rows(cta_buttons)}


@router.post(
    "/{onboarding_id}/cta_buttons",
    response_model=CTAButtonEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_cta_button(
    onboarding_id: int,
    cta_button_in: CTAButtonCreate,
    _current_user=Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    await _get_onboarding_or_404(db, onboarding_id)

    normalized_css_id = _validate_css_id(cta_button_in.css_id)
    await _ensure_css_id_is_unique(
        db,
        onboarding_id=onboarding_id,
        css_id=normalized_css_id,
    )

    cta_button = CTAButton(
        onboarding_id=onboarding_id,
        name=cta_button_in.name,
        button_text=cta_button_in.button_text,
        css_id=normalized_css_id,
    )

    db.add(cta_button)
    try:
        await db.commit()
        await db.refresh(cta_button)
    except IntegrityError:
        await db.rollback()
        _http_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DUPLICATE_CSS_ID",
            message="Ja existe um botao CTA com este ID CSS neste onboarding.",
        )
    except Exception:
        await db.rollback()
        _http_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="TRACKING_SAVE_FAILED",
            message="Nao foi possivel salvar o botao CTA.",
        )

    return {"data": cta_button}
