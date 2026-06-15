"""Vincula os GA4 Measurement IDs (G-...) aos clientes pelo nome.

OBS: Measurement ID (G-...) é referência; a API de dados do GA4 precisa do
Property ID numérico + service account com acesso. Estes G- ficam guardados
para referência e exibição.
"""
import asyncio
import logging

from sqlalchemy import select

from app.db import base as _base  # noqa: F401
from app.db.session import AsyncSessionLocal
from app.models.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# (trecho do nome do cliente, ILIKE) -> GA4 Measurement ID
GA4 = [
    ("BETHLEM", "G-NV7HZMFY8Q"),
    ("SCOPACASA", "G-P1Z14JNCJS"),
    ("MIGUEL HORWACZ", "G-E7P5FTJ3JJ"),
    ("BAZZANELLA", "G-VTM3JZZVYB"),
    ("GABRIEL MACHADO", "G-JSL20FM65J"),
    ("EJJEMED", "G-PLGMPBFXNN"),
    ("CAILLEAUX", "G-4HF0Y4ZHYS"),
    ("RONALDO GRANGEIRO", "G-1J27NSQVRB"),  # Total Fono
    ("SKINDOO", "G-4419FH8FBG"),
]


async def run() -> None:
    updated = 0
    async with AsyncSessionLocal() as db:
        for keyword, gid in GA4:
            rows = (await db.execute(
                select(Client).where(Client.name.ilike(f"%{keyword}%"))
            )).scalars().all()
            if not rows:
                logger.warning("Nenhum cliente para '%s'", keyword)
                continue
            for c in rows:
                c.ga4_measurement_id = gid
                updated += 1
                logger.info("GA4 %s -> %s", gid, c.name)
        await db.commit()
    logger.info("GA4 measurement IDs vinculados: %s", updated)


if __name__ == "__main__":
    asyncio.run(run())
