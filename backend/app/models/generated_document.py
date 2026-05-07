from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base_class import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    __table_args__ = (
        UniqueConstraint(
            "onboarding_id",
            "document_kind",
            name="uq_generated_documents_onboarding_kind",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("onboardings.id"), nullable=False, index=True
    )
    step_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    document_kind = Column(String, nullable=False)
    title = Column(String, nullable=False)
    markdown_content = Column(Text, nullable=False)
    review_status = Column(String, nullable=False, server_default="APPROVED")
    review_feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
