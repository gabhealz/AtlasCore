from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func

from app.db.base_class import Base


class LLMUsageEvent(Base):
    """Uma chamada de LLM do pipeline, com uso real de tokens e custo estimado.

    Agregavel por onboarding e, via clients.onboarding_id, por cliente — para
    saber o custo operacional de cada cliente.
    """

    __tablename__ = "llm_usage_events"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("onboardings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    web_searches = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
