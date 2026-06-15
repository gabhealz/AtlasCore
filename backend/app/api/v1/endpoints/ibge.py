from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import ibge as ibge_client
from app.models.user import User
from app.schemas.ibge import (
    EstadoPopulacaoResponse,
    MunicipioEnvelope,
    MunicipioListEnvelope,
    PiramideResponse,
)
from app.services import ibge_service

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])

# id IBGE da UF por sigla (para população estadual via N3).
UF_IDS = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}


@router.get("/resolve", response_model=MunicipioEnvelope)
async def resolve_municipio(
    city: str,
    uf: str,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    """Resolve cidade+UF (texto livre) em município IBGE com população e porte."""
    mun = await ibge_service.resolve_city(db, city, uf)
    if mun is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "MUNICIPIO_NOT_FOUND", "message": "Município não encontrado no IBGE."},
        )
    return {"data": mun}


@router.get("/municipios", response_model=MunicipioListEnvelope)
async def list_municipios(
    uf: str,
    q: str | None = None,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    rows = await ibge_service.search_municipios(db, uf, q)
    return {"data": rows}


@router.get("/municipios/{municipio_id}/piramide", response_model=PiramideResponse)
async def municipio_piramide(
    municipio_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    mun = await ibge_service.get_municipio(db, municipio_id)
    if mun is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "MUNICIPIO_NOT_FOUND", "message": "Município não encontrado."},
        )
    piramide = await ibge_service.get_piramide(db, mun)
    return {"municipio_id": municipio_id, "ano": mun.pyramid_ano, "data": piramide or []}


@router.get("/uf/{uf}/populacao", response_model=EstadoPopulacaoResponse)
async def uf_populacao(
    uf: str,
    current_user: User = Depends(allow_read),
):
    uf = uf.upper()
    uf_id = UF_IDS.get(uf)
    if uf_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UF inválida.")
    pop, ano = await ibge_client.fetch_populacao(f"N3[{uf_id}]")
    return {"uf": uf, "populacao": pop, "ano": ano}
