"""
SQLAlchemy model for users.
"""
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # 'user', 'admin', 'collection_steward', 'model_operator', 'security_auditor'

    # Relationships
    conversations = relationship("Conversation", back_populates="owner")
    messages = relationship("Message", back_populates="owner")
    audit_events = relationship("AuditEvent", back_populates="actor")
    owned_collections = relationship("Collection", back_populates="owner")
    owned_documents = relationship("Document", back_populates="owner")