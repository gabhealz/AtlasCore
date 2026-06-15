"""Tintim Webhook receiver.

Tintim works via push (webhooks), not pull. Each client gets a unique
webhook URL with a secret. When Tintim fires an event (new lead,
stage change, sale, etc.), it POSTs to our endpoint.

O schema exato do Tintim não é público, então a recepção é TOLERANTE: guardamos
o payload cru em `tintim_events` e extraímos os campos dos nomes mais comuns.
A métrica semanal (MetricSnapshot source='tintim') é RECOMPUTADA a partir dos
eventos da semana — isso torna a ingestão idempotente (reentregas não contam 2x).

Mapeamento de estágio → categoria (fácil de ajustar quando virmos os eventos reais):
- 'fechado'/'ganho'/'realizado'/'venda'/'won'  -> sale  (soma `value` em revenue)
- 'agend...'/'marcado'/'agendamento'            -> booking
- conversa criada / mensagem / 'lead'/'novo'    -> lead
- resto                                         -> other (guardado, ignorado na métrica)
"""

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.integration_setting import IntegrationSetting
from app.models.metric_snapshot import MetricSnapshot
from app.models.tintim_event import TintimEvent

logger = logging.getLogger(__name__)

router = APIRouter()


class TintimEventSchema(BaseModel):
    """Modelo flexível (referência) dos eventos do Tintim."""
    event_type: str | None = None
    phone: str | None = None
    name: str | None = None
    stage: str | None = None
    source: str | None = None
    value: float | None = None
    created_at: str | None = None


# --- Mapeamento estágio/evento -> categoria (AJUSTÁVEL) ---
SALE_KEYS = ("fechad", "ganho", "realizad", "venda", "won", "convertid", "compr")
BOOKING_KEYS = ("agend", "marcad", "agendamento", "consulta marcada", "scheduled")
LEAD_KEYS = ("lead", "novo", "nova conversa", "iniciad", "created", "criad", "aberto")


def categorize(event_type: str | None, stage: str | None) -> str:
    et = (event_type or "").lower()
    st = (stage or "").lower()
    blob = f"{et} {st}"
    if any(k in blob for k in SALE_KEYS):
        return "sale"
    if any(k in blob for k in BOOKING_KEYS):
        return "booking"
    if any(k in blob for k in LEAD_KEYS) or et in ("conversation_created", "message_created"):
        return "lead"
    # Por padrão, uma conversa/contato novo conta como lead.
    if "conversation" in et or "message" in et or "contact" in et:
        return "lead"
    return "other"


def generate_webhook_secret(client_id: int, secret_key: str) -> str:
    """Gera um secret determinístico de webhook por cliente."""
    raw = f"tintim-webhook-{client_id}-{secret_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _dig(d: dict, *keys: str):
    """Pega a primeira chave existente (suporta 'a.b' aninhado)."""
    for key in keys:
        if "." in key:
            cur = d
            ok = True
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok and cur not in (None, ""):
                return cur
        elif isinstance(d, dict) and d.get(key) not in (None, ""):
            return d[key]
    return None


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()) if isinstance(v, str) and "," in v else Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _parse_dt(v) -> datetime:
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        except (ValueError, OSError):
            pass
    if isinstance(v, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v[:26] if "." in v else v, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def _find_integration_by_secret(
    db: AsyncSession, webhook_secret: str
) -> IntegrationSetting | None:
    result = await db.execute(
        select(IntegrationSetting).where(
            IntegrationSetting.platform == "tintim",
            IntegrationSetting.account_id == webhook_secret,
            IntegrationSetting.is_active == True,  # noqa: E712
        )
    )
    return result.scalars().first()


async def _recompute_tintim_snapshot(
    db: AsyncSession, client_id: int, week_start: date
) -> dict:
    """Recomputa o MetricSnapshot (source='tintim') da semana a partir dos eventos."""
    res = await db.execute(
        select(TintimEvent).where(
            TintimEvent.client_id == client_id,
            TintimEvent.week_start == week_start,
        )
    )
    events = res.scalars().all()

    lead_keys: set[str] = set()
    booking_keys: set[str] = set()
    revenue = Decimal(0)
    for e in events:
        key = e.phone or e.external_event_id or f"id{e.id}"
        if e.category in ("lead", "booking", "sale"):
            lead_keys.add(key)
        if e.category in ("booking", "sale"):
            booking_keys.add(key)
        if e.category == "sale" and e.value:
            revenue += e.value

    leads = len(lead_keys)
    bookings = len(booking_keys)
    rate = round((bookings / leads) * 100, 2) if leads else None

    stmt = pg_insert(MetricSnapshot).values(
        client_id=client_id,
        week_start=week_start,
        date=week_start,
        source="tintim",
        conversions=leads,
        bookings=bookings,
        revenue=(revenue if revenue > 0 else None),
        whatsapp_to_booking_rate=rate,
    ).on_conflict_do_update(
        index_elements=["client_id", "week_start", "source"],
        set_={
            "conversions": leads,
            "bookings": bookings,
            "revenue": (revenue if revenue > 0 else None),
            "whatsapp_to_booking_rate": rate,
        },
    )
    await db.execute(stmt)
    await db.commit()
    return {"leads": leads, "bookings": bookings, "revenue": float(revenue)}


@router.post("/tintim/{webhook_secret}", status_code=status.HTTP_200_OK)
async def receive_tintim_webhook(
    webhook_secret: str,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
):
    """Recebe um evento do Tintim. Nunca retorna 5xx — sempre 200 com um ack."""
    integration = await _find_integration_by_secret(db, webhook_secret)
    if integration is None:
        logger.warning("Tintim webhook: secret desconhecido %s", webhook_secret[:8])
        return {"processed": False, "reason": "unknown_secret"}

    try:
        body = await request.json()
    except Exception:
        return {"processed": False, "reason": "invalid_body"}
    if not isinstance(body, dict):
        return {"processed": False, "reason": "non_object_body"}

    try:
        event_type = _dig(body, "event_type", "type", "event", "action")
        phone = _dig(body, "phone", "contact.phone", "lead.phone", "customer.phone", "from")
        name = _dig(body, "name", "contact.name", "lead.name", "customer.name")
        stage = _dig(body, "stage", "status", "etapa", "deal.stage", "funnel_stage", "step")
        source = _dig(body, "source", "utm_source", "origem", "campaign", "lead.source")
        value = _to_decimal(_dig(body, "value", "amount", "valor", "deal.value", "price"))
        external_id = _dig(body, "id", "event_id", "conversation_id", "lead.id", "deal.id")
        occurred_raw = _dig(body, "created_at", "occurred_at", "timestamp", "date", "updated_at")

        occurred_at = _parse_dt(occurred_raw)
        week_start = _monday(occurred_at.date())
        category = categorize(str(event_type) if event_type else None, str(stage) if stage else None)

        if external_id:
            dedupe_key = f"ext:{integration.client_id}:{external_id}:{category}"
        else:
            raw = f"{integration.client_id}|{phone}|{event_type}|{stage}|{occurred_at.isoformat()}"
            dedupe_key = "hash:" + hashlib.sha256(raw.encode()).hexdigest()[:32]

        # Dedupe
        existing = await db.execute(
            select(TintimEvent.id).where(TintimEvent.dedupe_key == dedupe_key)
        )
        if existing.scalars().first() is not None:
            return {"processed": False, "reason": "duplicate"}

        event = TintimEvent(
            client_id=integration.client_id,
            integration_id=integration.id,
            external_event_id=str(external_id) if external_id else None,
            event_type=str(event_type) if event_type else None,
            phone=str(phone) if phone else None,
            name=str(name) if name else None,
            stage=str(stage) if stage else None,
            source=str(source) if source else None,
            value=value,
            category=category,
            occurred_at=occurred_at,
            week_start=week_start,
            dedupe_key=dedupe_key,
            raw_json=body,
        )
        db.add(event)
        await db.commit()

        agg = await _recompute_tintim_snapshot(db, integration.client_id, week_start)
        logger.info(
            "Tintim event ok: client=%s category=%s week=%s agg=%s",
            integration.client_id, category, week_start, agg,
        )
        return {
            "processed": True,
            "client_id": integration.client_id,
            "category": category,
            "week_start": week_start.isoformat(),
            "aggregate": agg,
        }
    except Exception as exc:  # nunca quebra a ingestão
        logger.exception("Tintim webhook: erro ao processar evento: %s", exc)
        return {"processed": False, "reason": "processing_error"}
