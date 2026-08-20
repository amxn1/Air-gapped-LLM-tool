"""
SQLAlchemy model for model profiles.
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from ..database import Base


class ModelProfile(Base):
    __tablename__ = "model_profiles"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    format = Column(String, nullable=False)  # GGUF, Safetensors
    quantization = Column(String, nullable=True)
    context_length = Column(Integer, default=4096)
    max_output = Column(Integer, default=1024)
    hardware_profile = Column(String, default="CPU/GPU")
    checksum = Column(String(64), nullable=True)  # SHA-256
    approval_id = Column(String(50), nullable=True)
    status = Column(String, default="staged")  # staged, smoke_testing, active, deprecated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())