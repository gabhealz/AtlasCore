from pydantic import BaseModel, field_validator


class SeoKeywordSearchRequest(BaseModel):
    keywords: list[str]
    specialty: str | None = None

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [k.strip() for k in value if isinstance(k, str) and k.strip()]
        if not cleaned:
            raise ValueError("Informe ao menos uma palavra-chave.")
        # Teto defensivo para nao estourar custo da API numa unica busca.
        return cleaned[:20]


class SeoKeywordResult(BaseModel):
    keyword: str
    avg_monthly_searches: int | None = None
    cpc: float | None = None
    competition: str | None = None
    source: str
    from_cache: bool
    queried_at: str | None = None


class SeoInternalClient(BaseModel):
    id: int
    name: str
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool


class SeoInternalOnboarding(BaseModel):
    id: int
    doctor_name: str
    specialty: str | None = None
    status: str


class SeoInternalMatches(BaseModel):
    specialty: str | None = None
    clients: list[SeoInternalClient] = []
    onboardings: list[SeoInternalOnboarding] = []


class SeoKeywordSearchData(BaseModel):
    keywords: list[SeoKeywordResult] = []
    internal: SeoInternalMatches
    notes: list[str] = []
    location_code: int
    language_code: str


class SeoKeywordSearchEnvelope(BaseModel):
    data: SeoKeywordSearchData
