from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(20), nullable=False)  # meta, google, tintim
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(20), nullable=False, default="running"
    )  # running, success, failed, partial
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="sync_logs")
