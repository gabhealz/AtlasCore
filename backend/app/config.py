"""Atlas Core — Application Configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://atlas:atlas_dev@localhost:5432/atlas_core"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # JWT Authentication
    JWT_SECRET: str = "atlas-core-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # App
    APP_NAME: str = "Atlas Core"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # File uploads
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
