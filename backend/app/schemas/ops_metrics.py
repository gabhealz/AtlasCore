from datetime import date as datetime_date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .client import ClientResponse


class MetricSnapshotBase(BaseModel):
    client_id: int
    week_start: datetime_date
    date: datetime_date | None = None
    source: str
    impressions: int | None = Field(None, ge=0)
    clicks: int | None = Field(None, ge=0)
    ctr: float | None = Field(None, ge=0, le=100)
    cpc: float | None = Field(None, ge=0)
    ad_spend: float | None = Field(None, ge=0)
    conversions: int | None = Field(None, ge=0)
    cost_per_conversion: float | None = Field(None, ge=0)
    lp_to_whatsapp_rate: float | None = Field(None, ge=0, le=100)
    whatsapp_to_booking_rate: float | None = Field(None, ge=0, le=100)
    revenue: float | None = Field(None, ge=0)
    bookings: int | None = Field(None, ge=0)


class MetricSnapshotCreate(MetricSnapshotBase):
    pass


class MetricSnapshotResponse(MetricSnapshotBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignSnapshotBase(BaseModel):
    client_id: int
    week_start: datetime_date
    platform: str
    campaign_id: str
    campaign_name: str
    impressions: int | None = Field(None, ge=0)
    clicks: int | None = Field(None, ge=0)
    ctr: float | None = Field(None, ge=0, le=100)
    cpc: float | None = Field(None, ge=0)
    spend: float | None = Field(None, ge=0)
    conversions: int | None = Field(None, ge=0)


class CampaignSnapshotCreate(CampaignSnapshotBase):
    pass


class CampaignSnapshotResponse(CampaignSnapshotBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientDashboardResponse(BaseModel):
    client: ClientResponse
    current_week: MetricSnapshotResponse | None = None
    previous_week: MetricSnapshotResponse | None = None
    roi: float | None = None
    roas: float | None = None
    roi_change_pct: float | None = None
    revenue_change_pct: float | None = None
    bookings_change_pct: float | None = None
    health_status: str
    weekly_history: list[MetricSnapshotResponse]
    campaigns: list[CampaignSnapshotResponse]


class OpsDashboardEnvelope(BaseModel):
    data: list[ClientDashboardResponse]
