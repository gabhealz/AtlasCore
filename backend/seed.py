import asyncio

from sqlalchemy import select

from app.api.deps import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def seed_user():
    async with AsyncSessionLocal() as db:
        users_to_seed = [
            {"email": "admin@healz.com.br", "password": "admin", "role": "admin"},
            {
                "email": "operator@healz.com.br",
                "password": "operator",
                "role": "operator",
            },
            {
                "email": "reviewer@healz.com.br",
                "password": "reviewer",
                "role": "reviewer",
            },
        ]

        for u in users_to_seed:
            result = await db.execute(select(User).where(User.email == u["email"]))
            user = result.scalars().first()
            if not user:
                new_user = User(
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                )
                db.add(new_user)
                await db.commit()
                print(f"User {u['email']} created with role {u['role']}")
            else:
                print(f"User {u['email']} already exists")


if __name__ == "__main__":
    asyncio.run(seed_user())
