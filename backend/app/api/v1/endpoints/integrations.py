from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.encryption import decrypt_value, encrypt_value
from app.models.client import Client
from app.models.integration_setting import IntegrationSetting
from app.models.tintim_event import TintimEvent
from app.models.user import User
from app.schemas.integration import (
    IntegrationSettingCreate,
    IntegrationSettingEnvelope,
    IntegrationSettingListEnvelope,
    IntegrationSettingResponse,
    IntegrationSettingUpdate,
    IntegrationTestResult,
)

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])
allow_write = deps.RoleChecker(["admin", "operator"])


def _to_response(integration: IntegrationSetting) -> dict:
    """Convert model to response dict, replacing encrypted tokens with boolean flags."""
    return {
        "id": integration.id,
        "client_id": integration.client_id,
        "platform": integration.platform,
        "account_id": integration.account_id,
        "is_active": integration.is_active,
        "has_access_token": bool(integration.encrypted_access_token),
        "has_refresh_token": bool(integration.encrypted_refresh_token),
        "token_expires_at": integration.token_expires_at,
        "last_sync_at": integration.last_sync_at,
        "sync_status": integration.sync_status,
        "created_at": integration.created_at,
        "updated_at": integration.updated_at,
    }


async def _get_client_or_404(db: AsyncSession, client_id: int) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CLIENT_NOT_FOUND",
                "message": "Cliente nao encontrado.",
            },
        )
    return client


@router.get(
    "/clients/{client_id}/integrations",
    response_model=IntegrationSettingListEnvelope,
)
async def list_integrations(
    client_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    await _get_client_or_404(db, client_id)
    result = await db.execute(
        select(IntegrationSetting)
        .where(IntegrationSetting.client_id == client_id)
        .order_by(IntegrationSetting.platform)
    )
    integrations = result.scalars().all()
    return {"data": [_to_response(i) for i in integrations]}


@router.get("/clients/{client_id}/tintim-events")
async def list_tintim_events(
    client_id: int,
    limit: int = 50,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    """Debug: últimos eventos do Tintim recebidos para o cliente (ver o que chega)."""
    await _get_client_or_404(db, client_id)
    result = await db.execute(
        select(TintimEvent)
        .where(TintimEvent.client_id == client_id)
        .order_by(TintimEvent.id.desc())
        .limit(min(limit, 200))
    )
    events = result.scalars().all()
    return {
        "data": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "category": e.category,
                "phone": e.phone,
                "name": e.name,
                "stage": e.stage,
                "source": e.source,
                "value": float(e.value) if e.value is not None else None,
                "occurred_at": e.occurred_at,
                "week_start": e.week_start,
                "raw_json": e.raw_json,
            }
            for e in events
        ]
    }


@router.post(
    "/clients/{client_id}/integrations",
    response_model=IntegrationSettingEnvelope,
    status_code=status.HTTP_201_CREATED,
)
async def create_integration(
    client_id: int,
    integration_in: IntegrationSettingCreate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    await _get_client_or_404(db, client_id)

    # Check for existing integration on same platform
    existing = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.client_id == client_id,
            IntegrationSetting.platform == integration_in.platform,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INTEGRATION_EXISTS",
                "message": f"Integracao {integration_in.platform} ja existe para este cliente.",
            },
        )

    # Tintim usa o account_id como "webhook secret". Se não vier, geramos um.
    account_id = integration_in.account_id
    if integration_in.platform == "tintim" and not account_id:
        from app.core.config import settings
        from app.integrations.tintim_webhook import generate_webhook_secret
        account_id = generate_webhook_secret(client_id, settings.SECRET_KEY)

    integration = IntegrationSetting(
        client_id=client_id,
        platform=integration_in.platform,
        account_id=account_id,
        is_active=integration_in.is_active,
        encrypted_access_token=(
            encrypt_value(integration_in.access_token)
            if integration_in.access_token
            else None
        ),
        encrypted_refresh_token=(
            encrypt_value(integration_in.refresh_token)
            if integration_in.refresh_token
            else None
        ),
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return {"data": _to_response(integration)}


@router.patch(
    "/clients/{client_id}/integrations/{platform}",
    response_model=IntegrationSettingEnvelope,
)
async def update_integration(
    client_id: int,
    platform: str,
    integration_in: IntegrationSettingUpdate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(
        select(IntegrationSetting)
        .where(
            IntegrationSetting.client_id == client_id,
            IntegrationSetting.platform == platform,
        )
        .with_for_update()
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "INTEGRATION_NOT_FOUND",
                "message": "Integracao nao encontrada.",
            },
        )

    if integration_in.account_id is not None:
        integration.account_id = integration_in.account_id
    if integration_in.is_active is not None:
        integration.is_active = integration_in.is_active
    if integration_in.access_token is not None:
        integration.encrypted_access_token = encrypt_value(
            integration_in.access_token
        )
    if integration_in.refresh_token is not None:
        integration.encrypted_refresh_token = encrypt_value(
            integration_in.refresh_token
        )

    await db.commit()
    await db.refresh(integration)
    return {"data": _to_response(integration)}


@router.delete(
    "/clients/{client_id}/integrations/{platform}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_integration(
    client_id: int,
    platform: str,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(
        select(IntegrationSetting)
        .where(
            IntegrationSetting.client_id == client_id,
            IntegrationSetting.platform == platform,
        )
        .with_for_update()
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "INTEGRATION_NOT_FOUND",
                "message": "Integracao nao encontrada.",
            },
        )

    await db.delete(integration)
    await db.commit()


@router.post(
    "/clients/{client_id}/integrations/{platform}/test",
    response_model=IntegrationTestResult,
)
async def test_integration(
    client_id: int,
    platform: str,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.client_id == client_id,
            IntegrationSetting.platform == platform,
        )
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "INTEGRATION_NOT_FOUND",
                "message": "Integracao nao encontrada.",
            },
        )

    if not integration.encrypted_access_token:
        return IntegrationTestResult(
            platform=platform,
            success=False,
            message="Nenhum access token configurado.",
        )

    try:
        token = decrypt_value(integration.encrypted_access_token)
        account_id = integration.account_id or ""

        if platform == "meta":
            from app.integrations.meta_ads import test_connection
            result = test_connection(token, account_id)
            return IntegrationTestResult(
                platform=platform,
                success=result["success"],
                message=result["message"],
            )

        elif platform == "google":
            # Google uses refresh token (stored as access_token in our schema)
            from app.integrations.google_ads import test_connection
            result = test_connection(token, account_id)
            return IntegrationTestResult(
                platform=platform,
                success=result["success"],
                message=result["message"],
            )

        elif platform == "ga4":
            from app.integrations.ga4 import test_connection
            result = test_connection(token, account_id)
            return IntegrationTestResult(
                platform=platform,
                success=result["success"],
                message=result["message"],
            )

        elif platform == "tintim":
            # Tintim uses webhooks — just verify the webhook secret is configured
            return IntegrationTestResult(
                platform=platform,
                success=True,
                message=f"Webhook configurado. URL secreta: {account_id}",
            )

        else:
            return IntegrationTestResult(
                platform=platform,
                success=True,
                message="Token configurado e descriptografável.",
            )

    except Exception as e:
        return IntegrationTestResult(
            platform=platform,
            success=False,
            message=f"Erro ao testar conexão: {str(e)}",
        )
