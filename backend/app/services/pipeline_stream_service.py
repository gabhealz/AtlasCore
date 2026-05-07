import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.onboarding import Onboarding
from app.models.pipeline_event import PipelineEvent
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

PIPELINE_STATUS_EVENT = "pipeline_status"
PIPELINE_SNAPSHOT_STEP = "status_snapshot"
PIPELINE_SNAPSHOT_TRIGGER = "stream_connect"


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


class PipelineStreamService:
    def __init__(
        self,
        *,
        redis_client_factory: Callable[[], Any] | None = None,
        db_session_factory: Callable[[], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
        ping_interval_seconds: float = 1.0,
    ):
        self._redis_client_factory = redis_client_factory or self._build_redis_client
        self._db_session_factory = db_session_factory or AsyncSessionLocal
        self._clock = clock or self._utc_now
        self._ping_interval_seconds = ping_interval_seconds

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _build_redis_client():
        return redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    @staticmethod
    def _format_event(event_name: str, payload: dict[str, Any]) -> str:
        return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"

    @staticmethod
    def _format_keepalive() -> str:
        return ": ping\n\n"

    @staticmethod
    def _payload_key(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True)

    async def get_initial_payload(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
    ) -> dict[str, Any]:
        onboarding = await self._get_onboarding(db=db, onboarding_id=onboarding_id)
        latest_event = await self._get_latest_pipeline_event(
            db=db,
            onboarding_id=onboarding_id,
        )
        if latest_event is not None:
            return latest_event.payload

        snapshot_created_at = self._clock()
        if snapshot_created_at.tzinfo is None:
            snapshot_created_at = snapshot_created_at.replace(tzinfo=UTC)

        return {
            "onboarding_id": onboarding_id,
            "step_name": PIPELINE_SNAPSHOT_STEP,
            "from_status": onboarding.status,
            "to_status": onboarding.status,
            "trigger": PIPELINE_SNAPSHOT_TRIGGER,
            "created_at": _format_datetime_utc(snapshot_created_at),
        }

    async def iter_pipeline_events(
        self,
        *,
        onboarding_id: int,
        request: Request,
        initial_payload: dict[str, Any],
    ) -> AsyncIterator[str]:
        channel = PipelineService.build_channel(onboarding_id)
        redis_client = None
        pubsub = None

        try:
            redis_client = self._redis_client_factory()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)
            latest_initial_payload = await self._get_latest_payload_with_fresh_session(
                onboarding_id=onboarding_id
            )
            stream_initial_payload = latest_initial_payload or initial_payload
            last_emitted_payload_key = self._payload_key(stream_initial_payload)

            yield self._format_event(PIPELINE_STATUS_EVENT, stream_initial_payload)

            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=self._ping_interval_seconds,
                )
                if message is None:
                    yield self._format_keepalive()
                    continue

                payload = self._decode_pubsub_payload(message.get("data"))
                if payload is None:
                    continue

                payload_key = self._payload_key(payload)
                if payload_key == last_emitted_payload_key:
                    continue

                last_emitted_payload_key = payload_key

                yield self._format_event(PIPELINE_STATUS_EVENT, payload)
        except asyncio.CancelledError:
            raise
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                except Exception:
                    logger.exception(
                        "Failed to unsubscribe pipeline stream channel.",
                        extra={"onboarding_id": onboarding_id},
                    )

                try:
                    await pubsub.aclose()
                except Exception:
                    logger.exception(
                        "Failed to close pipeline pubsub.",
                        extra={"onboarding_id": onboarding_id},
                    )

            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    logger.exception(
                        "Failed to close pipeline redis client.",
                        extra={"onboarding_id": onboarding_id},
                    )

    async def _get_latest_payload_with_fresh_session(
        self,
        *,
        onboarding_id: int,
    ) -> dict[str, Any] | None:
        async with self._db_session_factory() as db:
            latest_event = await self._get_latest_pipeline_event(
                db=db,
                onboarding_id=onboarding_id,
            )

        if latest_event is None:
            return None

        return latest_event.payload

    async def _get_onboarding(
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
            _http_error(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="ONBOARDING_NOT_FOUND",
                message="Onboarding nao encontrado.",
            )

        return onboarding

    async def _get_latest_pipeline_event(
        self,
        *,
        db: AsyncSession,
        onboarding_id: int,
    ) -> PipelineEvent | None:
        result = await db.execute(
            select(PipelineEvent)
            .where(PipelineEvent.onboarding_id == onboarding_id)
            .order_by(desc(PipelineEvent.created_at), desc(PipelineEvent.id))
        )
        return result.scalars().first()

    def _decode_pubsub_payload(self, raw_payload: Any) -> dict[str, Any] | None:
        if raw_payload is None:
            return None

        try:
            if isinstance(raw_payload, bytes):
                raw_payload = raw_payload.decode("utf-8")

            if isinstance(raw_payload, str):
                return json.loads(raw_payload)

            if isinstance(raw_payload, dict):
                return raw_payload
        except json.JSONDecodeError:
            logger.warning("Discarding invalid pipeline pubsub payload.")

        return None
