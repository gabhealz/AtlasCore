from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    monthly_fee = Column(Numeric(10, 2), nullable=False)
    meta_account_id = Column(String, nullable=True)
    google_account_id = Column(String, nullable=True)
    tintim_id = Column(String, nullable=True)
    onboarding_id = Column(Integer, ForeignKey("onboardings.id"), nullable=True, unique=True)
    active_platforms = Column(String, default="meta,google")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    metric_snapshots = relationship(
        "MetricSnapshot", back_populates="client", lazy="selectin"
    )
    campaign_snapshots = relationship(
        "CampaignSnapshot", back_populates="client", lazy="selectin"
    )
    integration_settings = relationship(
        "IntegrationSetting", back_populates="client", lazy="selectin"
    )
    sync_logs = relationship(
        "SyncLog", back_populates="client", lazy="selectin"
    )
