from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User

router = APIRouter()

# Only Admins can access
allow_admin = deps.RoleChecker(["admin"])


@router.get("/users")
async def get_users(
    current_user: User = Depends(allow_admin),
    db: AsyncSession = Depends(deps.get_db),
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"data": [{"id": u.id, "email": u.email, "role": u.role} for u in users]}
