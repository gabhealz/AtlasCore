"""Benchmark model — stores AI-generated benchmarking documents."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Content — each section of the benchmark document
    # Structure: {
    #   "etapa_1_objetivo": { "title": "...", "content": "...", "data": {} },
    #   "etapa_2_personas": { "title": "...", "content": "...", "data": {} },
    #   "etapa_3_google": { "title": "...", "content": "...", "data": {} },
    #   "etapa_4_meta": { "title": "...", "content": "...", "data": {} },
    #   "etapa_5_sintese": { "title": "...", "content": "...", "data": {} },
    # }
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Executive summary generated from all sections
    executive_summary: Mapped[str | None] = mapped_column(Text)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default="generating"
    )  # generating, draft, approved, rejected
    
    # Current step being processed (for progress tracking)
    current_step: Mapped[int] = mapped_column(default=0)  # 0-5
    
    # HITL approval
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_notes: Mapped[str | None] = mapped_column(Text)

    # Metadata
    model_used: Mapped[str | None] = mapped_column(String(100))
    total_tokens: Mapped[int | None] = mapped_column()
    total_cost_usd: Mapped[float | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    client = relationship("Client", back_populates="benchmarks")
