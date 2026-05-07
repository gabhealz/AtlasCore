from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class Onboarding(Base):
    __tablename__ = "onboardings"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    target_audience = Column(Text, nullable=True)
    differentials = Column(Text, nullable=True)
    tone_of_voice = Column(Text, nullable=True)
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
