from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base_class import Base


class CTAButton(Base):
    __tablename__ = "cta_buttons"
    __table_args__ = (
        UniqueConstraint(
            "onboarding_id",
            "css_id",
            name="uq_cta_buttons_onboarding_css_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("onboardings.id"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    button_text = Column(String, nullable=False)
    css_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
