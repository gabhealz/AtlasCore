from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.seo import SeoKeywordSearchEnvelope, SeoKeywordSearchRequest
from app.services import seo_research_service

router = APIRouter()

allow_read = deps.RoleChecker(["admin", "operator", "reviewer"])


@router.post("/keywords", response_model=SeoKeywordSearchEnvelope)
async def search_seo_keywords(
    payload: SeoKeywordSearchRequest,
    current_user: User = Depends(allow_read),
    db: AsyncSession = Depends(deps.get_db),
):
    """Pesquisa volume/CPC de keywords (DataForSEO + cache) e matches internos."""
    data = await seo_research_service.search_keywords(
        db,
        terms=payload.keywords,
        specialty=payload.specialty,
    )
    return {"data": data}
