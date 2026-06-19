from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.api import deps
from app.models.campaign_snapshot import CampaignSnapshot
from app.models.client import Client
from app.models.metric_snapshot import MetricSnapshot
from app.models.user import User
from app.schemas.ops_metrics import (
    CampaignSnapshotCreate,
    ClientDashboardResponse,
    MetricSnapshotCreate,
    OpsDashboardEnvelope,
)
from app.schemas.client import ClientEnvelope

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])
allow_write = deps.RoleChecker(["admin", "operator"])


def _calculate_roi(
    revenue: float | None, monthly_fee: float | None, ad_spend: float | None
) -> float | None:
    if revenue is None:
        return None
    fee = float(monthly_fee) if monthly_fee is not None else 0.0
    spend = float(ad_spend) if ad_spend is not None else 0.0
    total_cost = (fee / 4) + spend
    if total_cost > 0:
        return float(revenue) / total_cost
    return None


def _calculate_roas(revenue: float | None, ad_spend: float | None) -> float | None:
    if revenue is None or ad_spend is None:
        return None
    spend = float(ad_spend)
    if spend > 0:
        return float(revenue) / spend
    return None


def _calculate_change_pct(
    current: float | None, previous: float | None
) -> float | None:
    if current is None or previous is None:
        return None
    curr = float(current)
    prev = float(previous)
    if prev > 0:
        return ((curr - prev) / prev) * 100
    return None


def _get_health_status(roi: float | None) -> str:
    if roi is None:
        return "red"
    if roi >= 3:
        return "green"
    if roi >= 1:
        return "yellow"
    return "red"


def _aggregate_metrics(snapshots: list[MetricSnapshot]) -> dict | None:
    if not snapshots:
        return None

    agg = {
        "impressions": sum((s.impressions or 0) for s in snapshots),
        "clicks": sum((s.clicks or 0) for s in snapshots),
        "ad_spend": sum((float(s.ad_spend) if s.ad_spend else 0) for s in snapshots),
        "conversions": sum((s.conversions or 0) for s in snapshots),
        "revenue": sum((float(s.revenue) if s.revenue else 0) for s in snapshots),
        "bookings": sum((s.bookings or 0) for s in snapshots),
        "lp_sessions": sum((s.lp_sessions or 0) for s in snapshots),
    }

    if agg["impressions"] > 0:
        agg["ctr"] = (agg["clicks"] / agg["impressions"]) * 100
    if agg["clicks"] > 0:
        agg["cpc"] = agg["ad_spend"] / agg["clicks"]
        # Taxa de conversão do site = leads (WhatsApp) / cliques.
        agg["lp_to_whatsapp_rate"] = (agg["conversions"] / agg["clicks"]) * 100
    if agg["conversions"] > 0:
        agg["cost_per_conversion"] = agg["ad_spend"] / agg["conversions"]
        # Taxa WhatsApp -> agendamento = agendamentos / leads.
        agg["whatsapp_to_booking_rate"] = (agg["bookings"] / agg["conversions"]) * 100

    return agg


def _build_snapshot_dict(client_id: int, week_start: date, agg: dict) -> dict:
    """Build a MetricSnapshotResponse-compatible dict from aggregated data."""
    now = datetime.now(timezone.utc)
    return {
        "id": 0,
        "client_id": client_id,
        "week_start": week_start,
        "source": "aggregated",
        "created_at": now,
        "updated_at": now,
        **agg,
    }


# P07: Batch-load all metrics for all clients in two queries instead of N+1
async def _load_metrics_for_clients(
    db: AsyncSession,
    client_ids: list[int],
    week_start: date,
) -> dict[int, list[MetricSnapshot]]:
    """Load MetricSnapshots for multiple clients in a single query."""
    result = await db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.client_id.in_(client_ids),
            MetricSnapshot.week_start == week_start,
        )
    )
    snapshots = result.scalars().all()

    grouped: dict[int, list[MetricSnapshot]] = {cid: [] for cid in client_ids}
    for snap in snapshots:
        grouped[snap.client_id].append(snap)

    return grouped


@router.get("/dashboard", response_model=OpsDashboardEnvelope)
async def get_ops_dashboard(
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    # Load all active clients
    clients_result = await db.execute(
        select(Client).where(Client.is_active == True)  # noqa: E712
    )
    clients = clients_result.scalars().all()

    if not clients:
        return {"data": []}

    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    previous_week_start = current_week_start - timedelta(days=7)

    client_ids = [c.id for c in clients]

    # P07: Only 2 queries total instead of 2*N
    curr_metrics = await _load_metrics_for_clients(db, client_ids, current_week_start)
    prev_metrics = await _load_metrics_for_clients(db, client_ids, previous_week_start)

    dashboard_data = []

    for client in clients:
        curr_agg = _aggregate_metrics(curr_metrics.get(client.id, []))
        prev_agg = _aggregate_metrics(prev_metrics.get(client.id, []))

        curr_week_data = (
            _build_snapshot_dict(client.id, current_week_start, curr_agg)
            if curr_agg
            else None
        )
        prev_week_data = (
            _build_snapshot_dict(client.id, previous_week_start, prev_agg)
            if prev_agg
            else None
        )

        roi = _calculate_roi(
            curr_agg["revenue"] if curr_agg else None,
            client.monthly_fee,
            curr_agg["ad_spend"] if curr_agg else None,
        )
        prev_roi = _calculate_roi(
            prev_agg["revenue"] if prev_agg else None,
            client.monthly_fee,
            prev_agg["ad_spend"] if prev_agg else None,
        )

        roas = _calculate_roas(
            curr_agg["revenue"] if curr_agg else None,
            curr_agg["ad_spend"] if curr_agg else None,
        )

        # Query last 12 weeks of metric snapshots for this client
        snapshots_result = await db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.client_id == client.id)
            .order_by(desc(MetricSnapshot.week_start))
            .limit(12)
        )
        snapshots = snapshots_result.scalars().all()
        weekly_history = [
            {
                "id": s.id,
                "client_id": s.client_id,
                "week_start": s.week_start,
                "source": s.source,
                "impressions": s.impressions,
                "clicks": s.clicks,
                "ad_spend": float(s.ad_spend) if s.ad_spend is not None else None,
                "conversions": s.conversions,
                "bookings": s.bookings,
                "revenue": float(s.revenue) if s.revenue is not None else None,
                "lp_sessions": s.lp_sessions,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in reversed(snapshots)  # chronological order
        ]

        dashboard_data.append(
            {
                "client": client,
                "current_week": curr_week_data,
                "previous_week": prev_week_data,
                "roi": roi,
                "roas": roas,
                "roi_change_pct": _calculate_change_pct(roi, prev_roi),
                "revenue_change_pct": _calculate_change_pct(
                    curr_agg["revenue"] if curr_agg else None,
                    prev_agg["revenue"] if prev_agg else None,
                ),
                "bookings_change_pct": _calculate_change_pct(
                    curr_agg["bookings"] if curr_agg else None,
                    prev_agg["bookings"] if prev_agg else None,
                ),
                "health_status": _get_health_status(roi),
                "weekly_history": weekly_history,
                "campaigns": [],
            }
        )

    return {"data": dashboard_data}


# P08: Added response_model | P09: Wrapped in {"data": ...} envelope
@router.get(
    "/clients/{client_id}/dashboard",
    response_model=ClientDashboardResponse,
)
async def get_client_dashboard(
    client_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    client_result = await db.execute(select(Client).where(Client.id == client_id))
    client = client_result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())

    # 8 weeks history
    history = []
    for i in range(8):
        ws = current_week_start - timedelta(days=7 * i)
        snap_result = await db.execute(
            select(MetricSnapshot).where(
                MetricSnapshot.client_id == client.id,
                MetricSnapshot.week_start == ws,
            )
        )
        agg = _aggregate_metrics(snap_result.scalars().all())
        if agg:
            history.append(_build_snapshot_dict(client.id, ws, agg))

    # Reverse history to be chronological
    history.reverse()

    curr_agg = next(
        (h for h in history if h["week_start"] == current_week_start), None
    )
    prev_agg = next(
        (
            h
            for h in history
            if h["week_start"] == current_week_start - timedelta(days=7)
        ),
        None,
    )

    roi = _calculate_roi(
        curr_agg["revenue"] if curr_agg else None,
        client.monthly_fee,
        curr_agg["ad_spend"] if curr_agg else None,
    )
    prev_roi = _calculate_roi(
        prev_agg["revenue"] if prev_agg else None,
        client.monthly_fee,
        prev_agg["ad_spend"] if prev_agg else None,
    )

    roas = _calculate_roas(
        curr_agg["revenue"] if curr_agg else None,
        curr_agg["ad_spend"] if curr_agg else None,
    )

    campaigns_result = await db.execute(
        select(CampaignSnapshot).where(
            CampaignSnapshot.client_id == client.id,
            CampaignSnapshot.week_start == current_week_start,
        )
    )
    campaigns = campaigns_result.scalars().all()

    return {
        "client": client,
        "current_week": curr_agg,
        "previous_week": prev_agg,
        "roi": roi,
        "roas": roas,
        "roi_change_pct": _calculate_change_pct(roi, prev_roi),
        "revenue_change_pct": _calculate_change_pct(
            curr_agg["revenue"] if curr_agg else None,
            prev_agg["revenue"] if prev_agg else None,
        ),
        "bookings_change_pct": _calculate_change_pct(
            curr_agg["bookings"] if curr_agg else None,
            prev_agg["bookings"] if prev_agg else None,
        ),
        "health_status": _get_health_status(roi),
        "weekly_history": history,
        "campaigns": campaigns,
    }


# P12: Explicit fields in upsert
@router.post("/clients/{client_id}/snapshots")
async def create_snapshot(
    client_id: int,
    snapshot_in: MetricSnapshotCreate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    values = snapshot_in.model_dump(exclude={"client_id"})
    values["client_id"] = client_id

    stmt = insert(MetricSnapshot).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["client_id", "week_start", "source"],
        set_={
            "impressions": stmt.excluded.impressions,
            "clicks": stmt.excluded.clicks,
            "ctr": stmt.excluded.ctr,
            "cpc": stmt.excluded.cpc,
            "ad_spend": stmt.excluded.ad_spend,
            "conversions": stmt.excluded.conversions,
            "cost_per_conversion": stmt.excluded.cost_per_conversion,
            "lp_to_whatsapp_rate": stmt.excluded.lp_to_whatsapp_rate,
            "whatsapp_to_booking_rate": stmt.excluded.whatsapp_to_booking_rate,
            "revenue": stmt.excluded.revenue,
            "bookings": stmt.excluded.bookings,
        },
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}


@router.post("/clients/{client_id}/campaigns")
async def create_campaign(
    client_id: int,
    campaign_in: CampaignSnapshotCreate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    campaign = CampaignSnapshot(
        client_id=client_id, **campaign_in.model_dump(exclude={"client_id"})
    )
    db.add(campaign)
    await db.commit()
    return {"status": "ok"}
