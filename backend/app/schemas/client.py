from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    name: str
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    monthly_fee: float
    meta_account_id: str | None = None
    google_account_id: str | None = None
    tintim_id: str | None = None
    active_platforms: str = "meta,google"


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    monthly_fee: float | None = None
    meta_account_id: str | None = None
    google_account_id: str | None = None
    tintim_id: str | None = None
    active_platforms: str | None = None
    is_active: bool | None = None


class ClientResponse(ClientBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientListEnvelope(BaseModel):
    data: list[ClientResponse]


class ClientEnvelope(BaseModel):
    data: ClientResponse
