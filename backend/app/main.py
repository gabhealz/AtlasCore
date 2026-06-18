from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
import app.db.base  # noqa: F401 (Ensures all models are loaded and mappers configured)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Atlas-Core API",
    description="API para orquestração de IA do Atlas-Core",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Adicionando um fallback health na raiz da porta 8000
@app.get("/health")
async def health():
    return {"status": "ok"}
