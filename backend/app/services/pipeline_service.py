import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.onboarding import Onboarding
from app.models.pipeline_event import PipelineEvent

logger = logging.getLogger(__name__)

PIPELINE_START_STEP = "pipeline_start"
PIPELINE_START_TRIGGER = "manual_start"
PIPELINE_PENDING_STATUS = "PENDING"
PIPELINE_RUNNING_STATUS = "RUNNING"
PIPELINE_AWAITING_REVIEW_STATUS = "AWAITING_REVIEW"
PIPELINE_FAILED_STATUS = "FAILED"


def _format_datetime_utc(value: datetime) -> str:
    normalized_value = value.astimezone(UTC)
    return normalized_value.isoformat().replace("+00:00", "Z")


def _http_error(
    *,
    status_code: int,
    error_code: str,
    message: str,
    extra_detail: dict[str, Any] | None = None,
) -> None:
    detail = {"error_code": error_code, "message": message}
    if extra_detail:
        detail.update(extra_detail)

    raise HTTPException(status_code=status_code, detail=detail)


class PipelineService:
    def __init__(
        self,
        *,
        redis_client_factory: Callable[[], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self._redis_client_factory = redis_client_factory or self._build_redis_client
        self._clock = clock or self._utc_now

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def build_channel(onboarding_id: int) -> str:
        return f"pipeline:onboarding:{onboarding_id}"

    @staticmethod
    def _build_redis_client():
        return redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def start_pipeline(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Onboarding)
            .where(Onboarding.id == onboarding_id)
            .with_for_update()
        )
        onboarding = result.scalars().first()
        if onboarding is None:
            _http_error(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="ONBOARDING_NOT_FOUND",
                message="Onboarding nao encontrado.",
            )

        current_status = onboarding.status
        if current_status not in {PIPELINE_PENDING_STATUS, PIPELINE_FAILED_STATUS}:
            _http_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_PIPELINE_STATE",
                message=(
                    "Este onboarding so pode iniciar ou tentar novamente o "
                    "pipeline nos estados PENDING ou FAILED."
                ),
                extra_detail={"current_status": current_status},
            )

        try:
            await self._create_pipeline_event(
                db=db,
                onboarding=onboarding,
                step_name=PIPELINE_START_STEP,
                to_status=PIPELINE_RUNNING_STATUS,
                trigger=PIPELINE_START_TRIGGER,
            )
        except Exception:
            _http_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="PIPELINE_START_FAILED",
                message="Nao foi possivel iniciar o pipeline.",
            )

        return {
            "onboarding_id": onboarding_id,
            "status": onboarding.status,
        }

    async def record_progress(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
        step_name: str,
        trigger: str,
        to_status: str = PIPELINE_RUNNING_STATUS,
        extra_payload: dict[str, Any] | None = None,
        auto_commit: bool = True,
        publish: bool = True,
    ) -> dict[str, Any]:
        onboarding = await self._get_onboarding_or_raise(
            db=db,
            onboarding_id=onboarding_id,
        )
        return await self._create_pipeline_event(
            db=db,
            onboarding=onboarding,
            step_name=step_name,
            to_status=to_status,
            trigger=trigger,
            extra_payload=extra_payload,
            auto_commit=auto_commit,
            publish=publish,
        )

    async def fail_pipeline(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
        step_name: str,
        trigger: str,
        error_code: str,
        error_message: str,
        attempt_count: int,
        agent_name: str,
        model: str,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        onboarding = await self._get_onboarding_or_raise(
            db=db,
            onboarding_id=onboarding_id,
        )
        failure_payload = {
            "attempt_count": attempt_count,
            "error_code": error_code,
            "error_message": error_message,
            "agent_name": agent_name,
            "model": model,
        }
        if extra_payload:
            failure_payload.update(extra_payload)

        return await self._create_pipeline_event(
            db=db,
            onboarding=onboarding,
            step_name=step_name,
            to_status=PIPELINE_FAILED_STATUS,
            trigger=trigger,
            extra_payload=failure_payload,
        )

    async def _create_pipeline_event(
        self,
        *,
        db: AsyncSession,
        onboarding: Onboarding,
        step_name: str,
        to_status: str,
        trigger: str,
        extra_payload: dict[str, Any] | None = None,
        auto_commit: bool = True,
        publish: bool = True,
    ) -> dict[str, Any]:
        event_created_at = self._clock()
        if event_created_at.tzinfo is None:
            event_created_at = event_created_at.replace(tzinfo=UTC)

        from_status = onboarding.status
        payload = {
            "onboarding_id": onboarding.id,
            "step_name": step_name,
            "from_status": from_status,
            "to_status": to_status,
            "trigger": trigger,
            "created_at": _format_datetime_utc(event_created_at),
        }
        if extra_payload:
            payload.update(extra_payload)

        onboarding.status = to_status
        pipeline_event = PipelineEvent(
            onboarding_id=onboarding.id,
            step_name=step_name,
            from_status=from_status,
            to_status=to_status,
            payload=payload,
            created_at=event_created_at,
        )
        db.add(pipeline_event)

        if not auto_commit:
            await db.flush()
            return payload

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        if publish:
            await self._publish_state_change(
                onboarding_id=onboarding.id,
                payload=payload,
            )
        return payload

    async def publish_state_change(
        self,
        *,
        onboarding_id: int,
        payload: dict[str, Any],
    ) -> None:
        await self._publish_state_change(onboarding_id=onboarding_id, payload=payload)

    async def _get_onboarding_or_raise(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
    ) -> Onboarding:
        result = await db.execute(
            select(Onboarding).where(Onboarding.id == onboarding_id)
        )
        onboarding = result.scalars().first()
        if onboarding is None:
            raise ValueError(f"Onboarding {onboarding_id} nao encontrado.")

        return onboarding

    async def _publish_state_change(
        self,
        *,
        onboarding_id: int,
        payload: dict[str, Any],
    ) -> None:
        redis_client = None
        try:
            redis_client = self._redis_client_factory()
            await redis_client.publish(
                self.build_channel(onboarding_id),
                json.dumps(payload),
            )
        except Exception:
            logger.exception(
                "Failed to publish pipeline event.",
                extra={"onboarding_id": onboarding_id},
            )
        finally:
            if redis_client is not None:
                await redis_client.aclose()
