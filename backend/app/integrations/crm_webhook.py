"""Webhook do CRM — negócio ganho vira cliente aqui.

Quando alguém marca um negócio como ganho no Vendly CRM, ele posta aqui o
retrato do que foi vendido: contato, valor, produto, por quais etapas passou
e o que foi conversado. Criamos o cliente como **rascunho** (`is_draft`),
porque o que o CRM sabe não basta pra operar: falta conta de anúncio,
contrato, propriedade do GA4. Alguém completa isso depois.

Autenticação por segredo compartilhado no header `X-Webhook-Secret`,
comparado em tempo constante. O mesmo segredo fica configurado do lado do
CRM, por empresa.

Idempotente pelo `deal.id`: o CRM retenta em caso de falha, e reentrega não
pode virar cliente duplicado. Segunda chamada com o mesmo negócio atualiza o
rascunho em vez de criar outro.
"""
import hmac
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api import deps
from app.core.config import settings
from app.models.client import Client

logger = logging.getLogger(__name__)

router = APIRouter()


class DealPayload(BaseModel):
    id: str
    title: str | None = None
    mrr: float | None = None
    setup_fee: float | None = None
    value: float | None = None
    contract_months: int | None = None
    product: str | None = None
    owner: str | None = None
    owner_email: str | None = None
    created_at: str | None = None
    closed_at: str | None = None


class ContactPayload(BaseModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    city: str | None = None
    state: str | None = None
    source: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class DealWonPayload(BaseModel):
    source: str = "vendly-crm"
    deal: DealPayload
    contact: ContactPayload = Field(default_factory=ContactPayload)
    stage_history: list[dict[str, Any]] = Field(default_factory=list)
    communications: list[dict[str, Any]] = Field(default_factory=list)


def _check_secret(received: str | None) -> None:
    expected = getattr(settings, "CRM_WEBHOOK_SECRET", "") or ""
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Integração com o CRM não configurada neste ambiente",
        )
    if not received or not hmac.compare_digest(received, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Segredo inválido")


def _to_decimal(value: float | None) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError):
        return Decimal(0)


def _client_name(payload: DealWonPayload) -> str:
    """Nome do cliente: empresa, senão a pessoa, senão o título do negócio."""
    return (
        (payload.contact.company or "").strip()
        or (payload.contact.name or "").strip()
        or (payload.deal.title or "").strip()
        or "Cliente sem nome"
    )


@router.post("/crm/deal-won", status_code=status.HTTP_200_OK)
async def receive_deal_won(
    payload: DealWonPayload,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    _check_secret(x_webhook_secret)

    existing = (
        await db.execute(select(Client).where(Client.crm_deal_id == payload.deal.id))
    ).scalar_one_or_none()

    # O CRM manda MRR e setup separados; aqui a mensalidade é o que interessa
    # pro cálculo de LTV e tempo de casa.
    monthly_fee = _to_decimal(payload.deal.mrr)
    dados = {
        "name": _client_name(payload),
        "specialty": payload.contact.custom_fields.get("especialidade")
        or payload.contact.custom_fields.get("specialty"),
        "city": payload.contact.city,
        "state": (payload.contact.state or "")[:2] or None,
        "phone": payload.contact.phone,
        "email": payload.contact.email,
        "monthly_fee": monthly_fee,
        "plan_name": payload.deal.product,
        "document": payload.contact.custom_fields.get("cnpj")
        or payload.contact.custom_fields.get("cpf"),
        "crm_payload": payload.model_dump(mode="json"),
    }

    if existing:
        # Reentrega ou negócio reaberto e ganho de novo: atualiza sem duplicar.
        for campo, valor in dados.items():
            if valor not in (None, ""):
                setattr(existing, campo, valor)
        await db.commit()
        await db.refresh(existing)
        logger.info(
            "CRM webhook: cliente %s atualizado a partir do negócio %s",
            existing.id,
            payload.deal.id,
        )
        return {"status": "updated", "client_id": existing.id, "is_draft": existing.is_draft}

    client = Client(
        **dados,
        crm_deal_id=payload.deal.id,
        is_active=True,
        is_draft=True,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    logger.info(
        "CRM webhook: cliente %s criado como rascunho a partir do negócio %s",
        client.id,
        payload.deal.id,
    )
    return {"status": "created", "client_id": client.id, "is_draft": True}
