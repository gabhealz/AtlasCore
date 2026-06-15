"""Orquestração IBGE: cache-or-fetch de municípios, população, porte e pirâmide."""

import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations import ibge
from app.models.ibge_municipio import IbgeMunicipio

# UF -> nome da capital (para classificar porte AA e marcar is_capital).
CAPITAIS = {
    "AC": "Rio Branco", "AL": "Maceió", "AP": "Macapá", "AM": "Manaus",
    "BA": "Salvador", "CE": "Fortaleza", "DF": "Brasília", "ES": "Vitória",
    "GO": "Goiânia", "MA": "São Luís", "MT": "Cuiabá", "MS": "Campo Grande",
    "MG": "Belo Horizonte", "PA": "Belém", "PB": "João Pessoa", "PR": "Curitiba",
    "PE": "Recife", "PI": "Teresina", "RJ": "Rio de Janeiro", "RN": "Natal",
    "RS": "Porto Alegre", "RO": "Porto Velho", "RR": "Boa Vista",
    "SC": "Florianópolis", "SP": "São Paulo", "SE": "Aracaju", "TO": "Palmas",
}


def normalize(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def classificar_porte(populacao: int | None, is_capital: bool) -> str | None:
    if is_capital:
        return "AA"
    if populacao is None:
        return None
    if populacao > 300_000:
        return "A"
    if populacao >= 100_000:
        return "B"
    return "C"


def _stale(updated_at) -> bool:
    if updated_at is None:
        return True
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - updated_at > timedelta(days=settings.IBGE_CACHE_TTL_DAYS)


async def ensure_uf_cached(db: AsyncSession, uf: str) -> None:
    """Garante que os municípios da UF estão no cache (lista, sem população)."""
    uf = uf.upper()
    count = await db.execute(
        select(func.count(IbgeMunicipio.id)).where(IbgeMunicipio.uf_sigla == uf)
    )
    if (count.scalar() or 0) > 0:
        return
    municipios = await ibge.fetch_municipios_uf(uf)
    cap_norm = normalize(CAPITAIS.get(uf))
    for m in municipios:
        is_cap = normalize(m["nome"]) == cap_norm
        db.add(IbgeMunicipio(
            id=m["id"], nome=m["nome"], uf_sigla=m["uf_sigla"],
            uf_id=m["uf_id"], uf_nome=m["uf_nome"], is_capital=is_cap,
        ))
    await db.commit()


async def _ensure_populacao(db: AsyncSession, mun: IbgeMunicipio) -> IbgeMunicipio:
    if mun.populacao is not None and not _stale(mun.updated_at):
        return mun
    pop, ano = await ibge.fetch_populacao(f"N6[{mun.id}]")
    if pop is not None:
        mun.populacao = pop
        mun.populacao_ano = ano
        mun.classificacao_porte = classificar_porte(pop, bool(mun.is_capital))
        await db.commit()
        await db.refresh(mun)
    elif mun.is_capital and not mun.classificacao_porte:
        mun.classificacao_porte = "AA"
        await db.commit()
    return mun


async def resolve_city(db: AsyncSession, city: str, uf: str) -> IbgeMunicipio | None:
    """Resolve cidade+UF (texto livre) -> município IBGE com população e porte."""
    if not uf:
        return None
    uf = uf.upper()
    await ensure_uf_cached(db, uf)
    target = normalize(city)
    rows = (await db.execute(
        select(IbgeMunicipio).where(IbgeMunicipio.uf_sigla == uf)
    )).scalars().all()
    match = next((m for m in rows if normalize(m.nome) == target), None)
    if match is None:
        match = next((m for m in rows if target and target in normalize(m.nome)), None)
    if match is None:
        return None
    return await _ensure_populacao(db, match)


async def get_municipio(db: AsyncSession, municipio_id: int) -> IbgeMunicipio | None:
    mun = (await db.execute(
        select(IbgeMunicipio).where(IbgeMunicipio.id == municipio_id)
    )).scalars().first()
    if mun is None:
        return None
    return await _ensure_populacao(db, mun)


async def get_piramide(db: AsyncSession, mun: IbgeMunicipio) -> list[dict] | None:
    if mun.pyramid_json and not _stale(mun.updated_at):
        return mun.pyramid_json
    piramide, ano = await ibge.fetch_piramide(mun.id)
    if piramide:
        mun.pyramid_json = piramide
        mun.pyramid_ano = ano
        await db.commit()
        await db.refresh(mun)
    return piramide


async def search_municipios(db: AsyncSession, uf: str, q: str | None) -> list[IbgeMunicipio]:
    uf = uf.upper()
    await ensure_uf_cached(db, uf)
    rows = (await db.execute(
        select(IbgeMunicipio).where(IbgeMunicipio.uf_sigla == uf).order_by(IbgeMunicipio.nome)
    )).scalars().all()
    if q:
        nq = normalize(q)
        rows = [m for m in rows if nq in normalize(m.nome)]
    return rows[:50]
