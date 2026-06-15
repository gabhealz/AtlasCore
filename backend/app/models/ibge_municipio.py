from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base_class import Base


class IbgeMunicipio(Base):
    """Cache de dados do IBGE por município (população, porte, pirâmide etária).

    `id` é o código IBGE do município. População vem do agregado 6579/9324
    (estimativa) e a pirâmide do Censo 2022 (agregado 9514). Reaproveitado do
    cache enquanto mais novo que IBGE_CACHE_TTL_DAYS.
    """

    __tablename__ = "ibge_municipios"

    id = Column(Integer, primary_key=True, index=True)  # código IBGE do município
    nome = Column(String, nullable=False)
    uf_sigla = Column(String(2), nullable=False, index=True)
    uf_id = Column(Integer, nullable=True)
    uf_nome = Column(String, nullable=True)
    is_capital = Column(Boolean, default=False)

    populacao = Column(BigInteger, nullable=True)
    populacao_ano = Column(Integer, nullable=True)
    classificacao_porte = Column(String, nullable=True)  # AA | A | B | C

    pyramid_json = Column(JSONB, nullable=True)  # [{faixa, homens, mulheres}]
    pyramid_ano = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
