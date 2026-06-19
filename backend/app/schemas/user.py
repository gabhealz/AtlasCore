from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "operator"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "operator"
    full_name: Optional[str] = None
    department: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


# ── Invitation ────────────────────────────────────────────────────────────────

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "operator"
    department: Optional[str] = None


class InvitationResponse(BaseModel):
    id: int
    email: str
    role: str
    department: Optional[str] = None
    invited_by_id: Optional[int] = None
    expires_at: datetime
    used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationInfo(BaseModel):
    email: str
    role: str
    department: Optional[str] = None


# ── Accept invite ─────────────────────────────────────────────────────────────

class AcceptInvite(BaseModel):
    token: str
    full_name: str
    password: str


# ── Forgot / Reset password ───────────────────────────────────────────────────

class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    password: str
