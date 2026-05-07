from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Atlas-Core"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/atlas_core"

    ALLOWED_EMAILS: str = (
        "admin@healz.com.br,operator@healz.com.br,reviewer@healz.com.br"
    )
    ALLOWED_EMAIL_DOMAIN: str = "healz.com.br"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_RESEARCH_MODEL: str = ""
    OPENAI_ENABLE_WEB_SEARCH: bool = True
    OPENAI_WEB_SEARCH_CONTEXT_SIZE: str = "high"
    OPENAI_TIMEOUT_SECONDS: float = 180
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_ZERO_DATA_RETENTION_CONFIRMED: bool = False
    REDIS_URL: str = "redis://redis:6379/0"
    MINIO_URL: str = "http://minio:9000"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "atlas-assets"
    MINIO_REGION: str = "us-east-1"

    @model_validator(mode="after")
    def validate_required_runtime_secrets(self) -> "Settings":
        if not self.SECRET_KEY.strip():
            raise ValueError(
                "SECRET_KEY precisa estar configurada no backend/.env."
            )

        if not self.MINIO_ACCESS_KEY.strip() or not self.MINIO_SECRET_KEY.strip():
            raise ValueError(
                "MINIO_ACCESS_KEY e MINIO_SECRET_KEY precisam estar configuradas."
            )

        return self

    @property
    def allowed_emails_list(self) -> list[str]:
        return [
            email.strip() for email in self.ALLOWED_EMAILS.split(",") if email.strip()
        ]

    @property
    def allowed_email_domain(self) -> str:
        return self.ALLOWED_EMAIL_DOMAIN.strip().lower().removeprefix("@")

    @property
    def backend_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    def is_allowed_email(self, email: str) -> bool:
        normalized_email = email.strip().lower()
        allowed_domain = self.allowed_email_domain
        if allowed_domain and normalized_email.endswith(f"@{allowed_domain}"):
            return True

        return normalized_email in {
            allowed_email.strip().lower()
            for allowed_email in self.allowed_emails_list
        }

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=ENV_FILE,
        extra="ignore",
    )


settings = Settings()
