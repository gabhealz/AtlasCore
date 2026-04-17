"""Atlas Core — Pydantic Schemas."""

from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ─── Auth ───────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Client ─────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str = Field(min_length=2)
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    instagram: str | None = None
    website: str | None = None
    monthly_budget: float | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    instagram: str | None = None
    website: str | None = None
    monthly_budget: float | None = None
    notes: str | None = None
    status: str | None = None


class ClientResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    specialty: str | None
    city: str | None
    state: str | None
    instagram: str | None
    website: str | None
    monthly_budget: float | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Transcript ─────────────────────────────────────────────────────────

class TranscriptResponse(BaseModel):
    id: UUID
    client_id: UUID
    uploaded_by: UUID
    title: str
    source: str
    raw_text: str
    parsed_data: dict | None
    parse_status: str
    file_name: str | None
    file_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptCreate(BaseModel):
    title: str = Field(min_length=2)
    source: str = "manual"
    raw_text: str = Field(min_length=10)


# ─── Benchmark ──────────────────────────────────────────────────────────

class BenchmarkResponse(BaseModel):
    id: UUID
    client_id: UUID
    generated_by: UUID
    content: dict[str, Any]
    executive_summary: str | None
    status: str
    current_step: int
    approved_by: UUID | None
    approved_at: datetime | None
    rejection_notes: str | None
    model_used: str | None
    total_tokens: int | None
    total_cost_usd: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BenchmarkApproval(BaseModel):
    approved: bool
    notes: str | None = None
