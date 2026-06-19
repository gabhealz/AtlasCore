from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, ForeignKey
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
    # Contrato (alimenta o cálculo de LTV / tempo de casa)
    plan_name = Column(String, nullable=True)  # AQF, Pareto, Carol, Mentoria, etc.
    external_code = Column(String, nullable=True)  # código do contrato (ex.: 2026/00046)
    document = Column(String, nullable=True)  # CPF/CNPJ
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    meta_account_id = Column(String, nullable=True)  # Meta Ad Account ID (act_...)
    google_account_id = Column(String, nullable=True)  # Google Ads Customer ID
    ga4_property_id = Column(String, nullable=True)  # GA4 Property ID (numérico, p/ Data API)
    ga4_measurement_id = Column(String, nullable=True)  # GA4 Measurement ID (G-...) referência
    tintim_id = Column(String, nullable=True)
    onboarding_id = Column(Integer, ForeignKey("onboardings.id", ondelete="SET NULL"), nullable=True, unique=True)
    active_platforms = Column(String, default="meta,google")
    is_active = Column(Boolean, default=True)
    # Rascunho criado automaticamente ao finalizar um onboarding (faltam dados/integrações).
    is_draft = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    metric_snapshots = relationship(
        "MetricSnapshot", back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
    campaign_snapshots = relationship(
        "CampaignSnapshot", back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
    sync_logs = relationship(
        "SyncLog", back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
