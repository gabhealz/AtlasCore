from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.client import Client
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientEnvelope,
    ClientListEnvelope,
    ClientUpdate,
)

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])
allow_write = deps.RoleChecker(["admin", "operator"])


async def _get_client_or_404(
    *,
    db: AsyncSession,
    client_id: int,
    for_update: bool = False,
) -> Client:
    query = select(Client).where(Client.id == client_id)
    if for_update:
        query = query.with_for_update()

    result = await db.execute(query)
    client = result.scalars().first()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "CLIENT_NOT_FOUND",
                "message": "Cliente nao encontrado.",
            },
        )

    return client


@router.get("", response_model=ClientListEnvelope)
async def get_clients(
    include_inactive: bool = Query(False, description="Incluir clientes inativos"),
    skip: int = Query(0, ge=0, description="Registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    query = select(Client).order_by(Client.name)

    # P10: Filter inactive clients by default
    if not include_inactive:
        query = query.where(Client.is_active == True)  # noqa: E712

    # P11: Pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    clients = result.scalars().all()
    return {"data": clients}


@router.post("", response_model=ClientEnvelope, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_in: ClientCreate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    client = Client(**client_in.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {"data": client}


@router.get("/{client_id}", response_model=ClientEnvelope)
async def get_client(
    client_id: int,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    client = await _get_client_or_404(db=db, client_id=client_id)
    return {"data": client}


@router.patch("/{client_id}", response_model=ClientEnvelope)
async def update_client(
    client_id: int,
    client_in: ClientUpdate,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    client = await _get_client_or_404(db=db, client_id=client_id, for_update=True)

    update_data = client_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)
    return {"data": client}


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: User = Depends(allow_write),
    db: AsyncSession = Depends(deps.get_db),
):
    client = await _get_client_or_404(db=db, client_id=client_id, for_update=True)
    client.is_active = False
    await db.commit()
