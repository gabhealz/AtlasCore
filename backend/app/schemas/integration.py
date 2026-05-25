from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationSettingBase(BaseModel):
    platform: str = Field(..., pattern="^(meta|google|ga4|tintim)$")
    account_id: str | None = None
    is_active: bool = True


class IntegrationSettingCreate(IntegrationSettingBase):
    """Schema for creating an integration — accepts plain-text tokens
    that will be encrypted before storage."""

    access_token: str | None = None
    refresh_token: str | None = None


class IntegrationSettingUpdate(BaseModel):
    account_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    is_active: bool | None = None


class IntegrationSettingResponse(IntegrationSettingBase):
    id: int
    client_id: int
    has_access_token: bool = False
    has_refresh_token: bool = False
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    sync_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationSettingListEnvelope(BaseModel):
    data: list[IntegrationSettingResponse]


class IntegrationSettingEnvelope(BaseModel):
    data: IntegrationSettingResponse


class IntegrationTestResult(BaseModel):
    platform: str
    success: bool
    message: str
