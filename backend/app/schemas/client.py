from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, computed_field


class ClientBase(BaseModel):
    name: str
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    monthly_fee: float
    plan_name: str | None = None
    external_code: str | None = None
    document: str | None = None
    contract_start_date: date | None = None
    contract_end_date: date | None = None
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
    plan_name: str | None = None
    external_code: str | None = None
    document: str | None = None
    contract_start_date: date | None = None
    contract_end_date: date | None = None
    meta_account_id: str | None = None
    google_account_id: str | None = None
    tintim_id: str | None = None
    active_platforms: str | None = None
    is_active: bool | None = None
    is_draft: bool | None = None


class ClientResponse(ClientBase):
    id: int
    is_active: bool
    is_draft: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tenure_days(self) -> int | None:
        """Dias desde o início do contrato (tempo de casa). Usado para LTV."""
        if not self.contract_start_date:
            return None
        return (date.today() - self.contract_start_date).days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tenure_months(self) -> int | None:
        """Meses completos desde o início do contrato (tempo de casa)."""
        if not self.contract_start_date:
            return None
        today = date.today()
        start = self.contract_start_date
        months = (today.year - start.year) * 12 + (today.month - start.month)
        if today.day < start.day:
            months -= 1
        return max(months, 0)


class ClientListEnvelope(BaseModel):
    data: list[ClientResponse]


class ClientEnvelope(BaseModel):
    data: ClientResponse
