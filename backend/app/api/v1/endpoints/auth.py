from fastapi import APIRouter, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token, UserLogin

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)


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
            detail={
                "error_code": "EMAIL_NOT_ALLOWED",
                "message": "E-mail nao pertence ao dominio autorizado.",
            },
        )

    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "INVALID_CREDENTIALS",
                "message": "Credenciais invalidas.",
            },
        )

    access_token = create_access_token(subject=user.id, role=user.role)
    response.set_cookie(
        key="atlas_access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="atlas_access_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return {"message": "Logout realizado com sucesso."}
