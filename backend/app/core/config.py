from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Atlas-Core"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    COOKIE_SECURE: bool = False

    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/atlas_core"

    ALLOWED_EMAILS: str = (
        "admin@healz.com.br,operator@healz.com.br,reviewer@healz.com.br"
    )
    ALLOWED_EMAIL_DOMAIN: str = "healz.com.br"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    OPENAI_API_KEY: str = ""
    # Modelo padrao para etapas baratas (ex.: reviewer de compliance).
    OPENAI_MODEL: str = "gpt-4.1-mini"
    # Modelo da etapa de pesquisa (researcher). O mini nao da conta de fazer
    # multiplas buscas web + consolidar 14 secoes; por isso a pesquisa usa um
    # modelo mais capaz por padrao. Ajustavel por OPENAI_RESEARCH_MODEL no .env.
    OPENAI_RESEARCH_MODEL: str = "gpt-4.1"
    OPENAI_ENABLE_WEB_SEARCH: bool = True
    OPENAI_WEB_SEARCH_CONTEXT_SIZE: str = "high"
    OPENAI_TIMEOUT_SECONDS: float = 180
    OPENAI_MAX_RETRIES: int = 3
    # Limite de tokens de saida da etapa de pesquisa. O documento tem 14 secoes
    # com tabelas; sem um teto alto, a resposta TRUNCA no meio (ex.: corta na
    # Analise de Demanda Google) e as secoes seguintes nunca sao geradas.
    OPENAI_MAX_OUTPUT_TOKENS: int = 16000
    OPENAI_ZERO_DATA_RETENTION_CONFIRMED: bool = False

    # --- Coleta de dados de mercado para o onboarding (fontes externas reais) ---
    # Estas sao credenciais GLOBAIS da agencia (nao por cliente). Quando vazias,
    # o coletor simplesmente nao usa a fonte e o pipeline segue so com web_search.
    # Meta Ad Library: anuncios ativos de concorrentes. Token do app da agencia.
    META_AD_LIBRARY_TOKEN: str = ""
    META_AD_LIBRARY_COUNTRY: str = "BR"
    # DataForSEO: volume de busca + CPC reais. Login/senha da API.
    DATAFORSEO_LOGIN: str = ""
    DATAFORSEO_PASSWORD: str = ""
    # Codigo de localizacao do DataForSEO (2076 = Brasil) e idioma.
    DATAFORSEO_LOCATION_CODE: int = 2076
    DATAFORSEO_LANGUAGE_CODE: str = "pt"
    # Validade do cache de keywords SEO (dias). Consultas mais novas que isso sao
    # reaproveitadas do banco em vez de chamar a API paga de novo.
    SEO_CACHE_TTL_DAYS: int = 30
    # Google Ads Keyword Planner: alternativa gratuita ao DataForSEO p/ volume+CPC.
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_CLIENT_ID: str = ""
    GOOGLE_ADS_CLIENT_SECRET: str = ""
    GOOGLE_ADS_REFRESH_TOKEN: str = ""
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = ""
    GOOGLE_ADS_CUSTOMER_ID: str = ""
    # Limite de itens coletados por fonte (evita prompt gigante / custo alto).
    MARKET_DATA_MAX_ITEMS: int = 15
    # Timeout das chamadas HTTP de coleta de mercado.
    MARKET_DATA_TIMEOUT_SECONDS: float = 30

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

    @property
    def meta_ad_library_enabled(self) -> bool:
        return bool(self.META_AD_LIBRARY_TOKEN.strip())

    @property
    def dataforseo_enabled(self) -> bool:
        return bool(
            self.DATAFORSEO_LOGIN.strip() and self.DATAFORSEO_PASSWORD.strip()
        )

    @property
    def google_ads_keywords_enabled(self) -> bool:
        return bool(
            self.GOOGLE_ADS_DEVELOPER_TOKEN.strip()
            and self.GOOGLE_ADS_CLIENT_ID.strip()
            and self.GOOGLE_ADS_CLIENT_SECRET.strip()
            and self.GOOGLE_ADS_REFRESH_TOKEN.strip()
            and self.GOOGLE_ADS_CUSTOMER_ID.strip()
        )

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
