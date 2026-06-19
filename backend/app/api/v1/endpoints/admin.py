import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.schemas.user import (
    InvitationCreate,
    InvitationResponse,
    UserResponse,
    UserUpdate,
)
from app.services.email_service import send_invite_email

router = APIRouter()

allow_admin = deps.RoleChecker(["admin"])

_INVITE_EXPIRE_HOURS = 72


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def get_users(
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail={"error_code": "USER_NOT_FOUND", "message": "Usuário não encontrado."})

    # Prevent admin from deactivating their own account
    if user.id == current_user.id and body.is_active is False:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "CANNOT_DEACTIVATE_SELF", "message": "Você não pode desativar sua própria conta."},
        )

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        if body.role not in ("admin", "operator", "reviewer"):
            raise HTTPException(status_code=422, detail={"error_code": "INVALID_ROLE", "message": "Role inválida."})
        user.role = body.role
    if body.department is not None:
        user.department = body.department
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    return user


# ── Invitations ───────────────────────────────────────────────────────────────

@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    body: InvitationCreate,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    # Check email domain
    from app.core.config import settings
    if not settings.is_allowed_email(body.email):
        raise HTTPException(
            status_code=422,
            detail={"error_code": "EMAIL_NOT_ALLOWED", "message": "Email fora do domínio autorizado (healz.com.br)."},
        )

    # Check no active user with that email
    existing_user = await db.execute(select(User).where(User.email == body.email))
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=409,
            detail={"error_code": "EMAIL_TAKEN", "message": "Já existe uma conta com este email."},
        )

    # Invalidate any previous pending invite for this email
    old_invites = await db.execute(
        select(UserInvitation).where(
            UserInvitation.email == body.email,
            UserInvitation.used_at.is_(None),
        )
    )
    for old in old_invites.scalars().all():
        old.used_at = datetime.now(timezone.utc)

    token_str = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=_INVITE_EXPIRE_HOURS)
    invite = UserInvitation(
        email=body.email,
        token=token_str,
        role=body.role,
        department=body.department,
        invited_by_id=current_user.id,
        expires_at=expires,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    from app.core.config import settings as cfg
    invite_url = f"{cfg.APP_BASE_URL}/accept-invite?token={token_str}"
    invited_by_name = current_user.full_name or current_user.email.split("@")[0]
    await send_invite_email(body.email, invite_url, invited_by_name)

    return invite


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserInvitation)
        .where(UserInvitation.used_at.is_(None), UserInvitation.expires_at > now)
        .order_by(UserInvitation.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invitation_id: int,
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(
        select(UserInvitation).where(UserInvitation.id == invitation_id)
    )
    invite = result.scalars().first()
    if not invite:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Convite não encontrado."})
    invite.used_at = datetime.now(timezone.utc)
    await db.commit()
