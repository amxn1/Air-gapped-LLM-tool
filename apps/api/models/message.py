"""
SQLAlchemy model for messages.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, nullable=False)  # e.g., 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    owner = relationship("User", back_populates="messages")