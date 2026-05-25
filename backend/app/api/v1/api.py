from fastapi import APIRouter

from .endpoints import admin, assets, auth, clients, health, integrations, onboardings, ops_metrics, stream, tracking
from app.integrations.tintim_webhook import router as tintim_webhook_router

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
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(ops_metrics.router, prefix="/ops", tags=["ops"])
api_router.include_router(integrations.router, prefix="/ops", tags=["integrations"])
api_router.include_router(tintim_webhook_router, prefix="/webhooks", tags=["webhooks"])

