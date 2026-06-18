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


class CampaignSnapshot(Base):
    __tablename__ = "campaign_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    platform = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    campaign_name = Column(String, nullable=False)

    impressions = Column(BigInteger, nullable=True)
    clicks = Column(Integer, nullable=True)
    ctr = Column(Numeric(8, 4), nullable=True)
    cpc = Column(Numeric(10, 2), nullable=True)
    spend = Column(Numeric(10, 2), nullable=True)
    conversions = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client = relationship("Client", back_populates="campaign_snapshots")

    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "week_start",
            "platform",
            "campaign_id",
            name="uq_campaign_client_week_platform_id",
        ),
    )
