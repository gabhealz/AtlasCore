from fastapi import APIRouter

from .endpoints import admin, assets, auth, health, onboardings, stream, tracking

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    onboardings.router, prefix="/onboardings", tags=["onboardings"]
)
api_router.include_router(stream.router, prefix="/onboardings", tags=["stream"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
