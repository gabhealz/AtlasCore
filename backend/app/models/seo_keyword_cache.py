from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base_class import Base


class SeoKeywordCache(Base):
    """Cache persistente de consultas de keyword no DataForSEO.

    Cada (keyword, location_code, language_code) guarda o ultimo resultado de
    volume/CPC/competicao, com `queried_at` para politica de validade. Evita
    repetir requisicoes pagas e funciona como base de dados SEO interna da Healz.
    """

    __tablename__ = "seo_keyword_cache"
    __table_args__ = (
        UniqueConstraint(
            "keyword",
            "location_code",
            "language_code",
            name="uq_seo_keyword_cache_keyword_loc_lang",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False, index=True)
    location_code = Column(Integer, nullable=False)
    language_code = Column(String, nullable=False)
    avg_monthly_searches = Column(Integer, nullable=True)
    cpc = Column(Numeric(10, 2), nullable=True)
    competition = Column(String, nullable=True)
    source = Column(String, nullable=False)
    queried_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
