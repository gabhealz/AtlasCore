from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.db.base_class import Base


class UploadedAsset(Base):
    __tablename__ = "uploaded_assets"

    id = Column(Integer, primary_key=True, index=True)
    onboarding_id = Column(
        Integer, ForeignKey("onboardings.id"), nullable=False, index=True
    )
    asset_kind = Column(String, nullable=False)
    asset_category = Column(String, nullable=True)
    original_filename = Column(String, nullable=False)
    object_key = Column(String, nullable=False, unique=True)
    storage_url = Column(String, nullable=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
