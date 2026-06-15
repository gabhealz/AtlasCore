from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base_class import Base


class TintimEvent(Base):
    """Evento bruto recebido do webhook do Tintim.

    Guardamos o payload cru (`raw_json`) para podermos mapear os campos reais
    depois que o webhook estiver apontado, sem perder nada. A métrica semanal
    (MetricSnapshot source='tintim') é recomputada a partir desta tabela, o que
    torna a ingestão idempotente (reentregas/duplicatas não contam em dobro).
    """

    __tablename__ = "tintim_events"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    integration_id = Column(
        Integer, ForeignKey("integration_settings.id"), nullable=True
    )

    external_event_id = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    name = Column(String, nullable=True)
    stage = Column(String, nullable=True)
    source = Column(String, nullable=True)  # origem/campanha (utm)
    value = Column(Numeric(10, 2), nullable=True)
    category = Column(String, nullable=True)  # lead | booking | sale | other

    occurred_at = Column(DateTime(timezone=True), nullable=True)
    week_start = Column(Date, nullable=False, index=True)
    dedupe_key = Column(String, nullable=False)
    raw_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_tintim_event_dedupe"),
    )
