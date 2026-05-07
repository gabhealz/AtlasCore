from typing import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def _invalid_token_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "INVALID_TOKEN", "message": message},
    )


async def _get_user_from_token(*, db: AsyncSession, token: str) -> User:
    if not token:
        raise _invalid_token_exception("Token invalido ou expirado.")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise _invalid_token_exception("Token invalido.")
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise _invalid_token_exception("Token invalido.")
    except jwt.PyJWTError:
        raise _invalid_token_exception("Token invalido ou expirado.")

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "USER_NOT_FOUND",
                "message": "Usuario nao encontrado.",
            },
        )

    return user


async def resolve_user_from_token(*, db: AsyncSession, token: str) -> User:
    return await _get_user_from_token(db=db, token=token)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    return await resolve_user_from_token(db=db, token=token)


async def get_current_user_from_stream_token(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Query(default=None),
) -> User:
    if not access_token:
        raise _invalid_token_exception("Token invalido ou expirado.")

    return await resolve_user_from_token(db=db, token=access_token)


def ensure_role(user: User, allowed_roles: list[str]) -> User:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "INSUFFICIENT_PERMISSIONS",
                "message": "Permissoes insuficientes.",
            },
        )

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        return ensure_role(user, self.allowed_roles)
