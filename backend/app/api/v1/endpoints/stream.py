from fastapi import APIRouter, Cookie, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api import deps
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.pipeline_stream_service import PipelineStreamService

router = APIRouter()

ALLOW_READ_ROLES = ["admin", "operator", "reviewer"]


def get_pipeline_stream_service() -> PipelineStreamService:
    return PipelineStreamService()


@router.get("/{onboarding_id}/stream")
async def stream_onboarding_pipeline(
    onboarding_id: int,
    request: Request,
    access_token: str | None = Query(default=None),
    atlas_access_token: str | None = Cookie(default=None),
    pipeline_stream_service: PipelineStreamService = Depends(
        get_pipeline_stream_service
    ),
):
    token = atlas_access_token or access_token
    if not token:
        raise deps._invalid_token_exception("Token invalido ou expirado.")

    async with AsyncSessionLocal() as db:
        current_user: User = await deps.resolve_user_from_token(
            db=db,
            token=token,
        )
        deps.ensure_role(current_user, ALLOW_READ_ROLES)
        initial_payload = await pipeline_stream_service.get_initial_payload(
            db=db,
            onboarding_id=onboarding_id,
        )

    return StreamingResponse(
        pipeline_stream_service.iter_pipeline_events(
            onboarding_id=onboarding_id,
            request=request,
            initial_payload=initial_payload,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
