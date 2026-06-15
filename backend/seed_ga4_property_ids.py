"""Vincula os GA4 Property IDs (numéricos, p/ a Data API) aos clientes pelo nome."""
import asyncio
import logging

from sqlalchemy import select

from app.db import base as _base  # noqa: F401
from app.db.session import AsyncSessionLocal
from app.models.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# (trecho do nome do cliente, ILIKE) -> GA4 Property ID
PROPS = [
    ("BETHLEM", "424939283"),
    ("SCOPACASA", "445003042"),
    ("MIGUEL HORWACZ", "486732504"),
    ("BAZZANELLA", "514569205"),
    ("GABRIEL MACHADO", "531558963"),
    ("EJJEMED", "434429199"),
    ("CAILLEAUX", "527700880"),
    ("RONALDO GRANGEIRO", "475676069"),  # Total Fono
    ("SKINDOO", "514495750"),
    ("CAROLINE FERREIRA", "537728135"),
    ("RODRIGO FREDDI", "537555978"),
    ("CANTARELLI", "533467173"),  # Carolina Cantarelli
    ("ANDRE LUIZ TORRES", "539393533"),
    ("NATALIA SILVEIRA", "368799250"),
]


async def run() -> None:
    updated = 0
    async with AsyncSessionLocal() as db:
        for keyword, pid in PROPS:
            rows = (await db.execute(
                select(Client).where(Client.name.ilike(f"%{keyword}%"))
            )).scalars().all()
            if not rows:
                logger.warning("Nenhum cliente para '%s'", keyword)
                continue
            for c in rows:
                c.ga4_property_id = pid
                updated += 1
                logger.info("GA4 property %s -> %s", pid, c.name)
        await db.commit()
    logger.info("GA4 property IDs vinculados: %s", updated)


if __name__ == "__main__":
    asyncio.run(run())
