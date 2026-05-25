"""Tintim Webhook receiver.

Tintim works via push (webhooks), not pull. Each client gets a unique
webhook URL with a secret. When Tintim fires an event (new lead,
stage change, etc.), it POSTs to our endpoint.
"""

import hashlib
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.integration_setting import IntegrationSetting

logger = logging.getLogger(__name__)

router = APIRouter()


class TintimEvent(BaseModel):
    """Flexible model for Tintim webhook events."""
    event_type: str | None = None        # conversation_created, conversation_updated, message_created
    phone: str | None = None
    name: str | None = None
    stage: str | None = None             # etapa do funil no Tintim
    source: str | None = None            # utm_source, origem do lead
    value: float | None = None           # valor da venda, se houver
    created_at: str | None = None


def generate_webhook_secret(client_id: int, secret_key: str) -> str:
    """Generate a deterministic webhook secret for a client.

    Uses HMAC-like hashing so the same client always gets the same URL,
    and we can verify incoming requests without DB lookups.
    """
    raw = f"tintim-webhook-{client_id}-{secret_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


async def _find_client_by_webhook_secret(
    db: AsyncSession,
    webhook_secret: str,
) -> int | None:
    """Find the client_id that matches this webhook secret.

    We look at all tintim IntegrationSettings and check which one
    has an account_id matching the secret.
    """
    result = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.platform == "tintim",
            IntegrationSetting.account_id == webhook_secret,
            IntegrationSetting.is_active == True,
        )
    )
    integration = result.scalars().first()
    if integration:
        return integration.client_id
    return None


@router.post("/tintim/{webhook_secret}", status_code=status.HTTP_200_OK)
async def receive_tintim_webhook(
    webhook_secret: str,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
):
    """Receive a webhook event from Tintim.

    The webhook_secret in the URL identifies which client this data belongs to.
    Tintim sends various event types (conversation_created, conversation_updated, etc.).
    """
    # Find the client by webhook secret
    client_id = await _find_client_by_webhook_secret(db, webhook_secret)
    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook secret inválido.",
        )

    # Parse the raw body — Tintim's payload format can vary
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corpo da requisição inválido.",
        )

    event_type = body.get("event_type", body.get("type", "unknown"))

    logger.info(
        "Tintim webhook received: client_id=%s event_type=%s",
        client_id,
        event_type,
    )

    # TODO Phase 2.1: Process events and update MetricSnapshot
    # - conversation_created → increment leads count
    # - conversation_updated (stage=agendado) → increment appointments
    # - conversation_updated (stage=fechado) → increment revenue + sales

    # For now, just log and acknowledge
    return {
        "status": "received",
        "client_id": client_id,
        "event_type": event_type,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
