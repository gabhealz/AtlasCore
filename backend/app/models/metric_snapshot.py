from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    date = Column(Date, nullable=True, index=True)
    source = Column(String, nullable=False)

    impressions = Column(BigInteger, nullable=True)
    clicks = Column(Integer, nullable=True)
    ctr = Column(Numeric(8, 4), nullable=True)
    cpc = Column(Numeric(10, 2), nullable=True)
    ad_spend = Column(Numeric(10, 2), nullable=True)
    conversions = Column(Integer, nullable=True)
    cost_per_conversion = Column(Numeric(10, 2), nullable=True)
    lp_to_whatsapp_rate = Column(Numeric(8, 4), nullable=True)
    whatsapp_to_booking_rate = Column(Numeric(8, 4), nullable=True)

    revenue = Column(Numeric(10, 2), nullable=True)
    bookings = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    client = relationship("Client", back_populates="metric_snapshots")

    __table_args__ = (
        UniqueConstraint(
            "client_id", "week_start", "source", name="uq_client_week_source"
        ),
    )
