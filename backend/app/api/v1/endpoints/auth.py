import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.schemas.user import (
    AcceptInvite,
    ForgotPassword,
    InvitationInfo,
    ResetPassword,
    Token,
    UserLogin,
    UserResponse,
)
from app.services.email_service import send_invite_email, send_password_reset_email

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)

_INVITE_EXPIRE_HOURS = 72
_RESET_EXPIRE_HOURS = 1


def _issue_token(user: User) -> str:
    return create_access_token(
        subject=user.id,
        role=user.role,
        email=user.email,
        name=user.full_name or user.email.split("@")[0],
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="atlas_access_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    user_in: UserLogin,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
):
    if not settings.is_allowed_email(user_in.email):
        raise HTTPException(
            status_code=403,
            detail={"error_code": "EMAIL_NOT_ALLOWED", "message": "E-mail não pertence ao domínio autorizado."},
        )

    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Credenciais inválidas."},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={"error_code": "USER_INACTIVE", "message": "Conta desativada. Contate o administrador."},
        )

    token = _issue_token(user)
    _set_auth_cookie(response, token)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="atlas_access_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return {"message": "Logout realizado com sucesso."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(deps.get_current_user)):
    return current_user


# ── Accept invite ─────────────────────────────────────────────────────────────

@router.get("/invitation-info", response_model=InvitationInfo)
async def get_invitation_info(token: str, db: AsyncSession = Depends(deps.get_db)):
    invite = await _get_valid_invite(db, token)
    return InvitationInfo(email=invite.email, role=invite.role, department=invite.department)


@router.post("/accept-invite", response_model=Token)
@limiter.limit("10/minute")
async def accept_invite(
    request: Request,
    body: AcceptInvite,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
):
    invite = await _get_valid_invite(db, body.token)

    # Ensure no existing user with that email
    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"error_code": "EMAIL_TAKEN", "message": "Já existe uma conta com este email."},
        )

    user = User(
        email=invite.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name.strip(),
        role=invite.role,
        department=invite.department,
        is_active=True,
    )
    db.add(user)

    invite.used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    token = _issue_token(user)
    _set_auth_cookie(response, token)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


# ── Forgot / Reset password ───────────────────────────────────────────────────

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPassword,
    db: AsyncSession = Depends(deps.get_db),
):
    # Always return 200 to avoid email enumeration
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))  # noqa: E712
    user = result.scalars().first()

    if user:
        token_str = secrets.token_hex(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=_RESET_EXPIRE_HOURS)
        prt = PasswordResetToken(user_id=user.id, token=token_str, expires_at=expires)
        db.add(prt)
        await db.commit()

        reset_url = f"{settings.APP_BASE_URL}/reset-password?token={token_str}"
        await send_password_reset_email(user.email, reset_url)

    return {"message": "Se esse email existir no sistema, você receberá as instruções em breve."}


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    body: ResetPassword,
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    prt = result.scalars().first()

    now = datetime.now(timezone.utc)
    if not prt or prt.used_at or prt.expires_at < now:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_TOKEN", "message": "Link inválido ou expirado."},
        )

    user_result = await db.execute(select(User).where(User.id == prt.user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_TOKEN", "message": "Link inválido ou expirado."},
        )

    user.hashed_password = get_password_hash(body.password)
    prt.used_at = now
    await db.commit()

    return {"message": "Senha redefinida com sucesso."}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_valid_invite(db: AsyncSession, token: str) -> UserInvitation:
    result = await db.execute(
        select(UserInvitation).where(UserInvitation.token == token)
    )
    invite = result.scalars().first()
    now = datetime.now(timezone.utc)

    if not invite:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "INVITE_NOT_FOUND", "message": "Convite não encontrado."},
        )
    if invite.used_at:
        raise HTTPException(
            status_code=410,
            detail={"error_code": "INVITE_USED", "message": "Este convite já foi utilizado."},
        )
    if invite.expires_at < now:
        raise HTTPException(
            status_code=410,
            detail={"error_code": "INVITE_EXPIRED", "message": "Este convite expirou."},
        )
    return invite
