"""
SQLAlchemy model for audit events.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    object_type = Column(String, nullable=True)
    object_id = Column(String, nullable=True)
    result = Column(String(20), nullable=True)  # success, failure
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    request_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)

    # Relationships
    actor = relationship("User", back_populates="audit_events")