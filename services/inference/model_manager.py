"""
Model profile management and lifecycle operations for the inference service.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from apps.api import models

logger = logging.getLogger(__name__)


@dataclass
class ModelProfile:
    """
    Data class representing a model profile for inference.
    """
    id: int
    model_name: str
    version: str
    format: str  # GGUF, Safetensors
    quantization: Optional[str] = "q4_0"
    context_length: int = 4096
    max_output: int = 1024
    hardware_profile: str = "CPU/GPU"
    checksum: Optional[str] = None
    approval_id: Optional[str] = None
    status: str = "staged"  # staged, smoke_testing, active, deprecated


def get_model_profile(db: Session, model_id: int) -> Optional[ModelProfile]:
    """Retrieve a model profile from the database by ID."""
    db_model = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
    if db_model:
        return _to_dataclass(db_model)
    return None


def get_active_model_profile(db: Session) -> Optional[ModelProfile]:
    """Retrieve the currently active model profile."""
    db_model = db.query(models.ModelProfile).filter(models.ModelProfile.status == "active").first()
    if db_model:
        return _to_dataclass(db_model)
    # If no active model profile, return the first available staged/registered profile
    db_fallback = db.query(models.ModelProfile).first()
    if db_fallback:
        return _to_dataclass(db_fallback)
    # Default built-in profile if database is entirely empty
    return ModelProfile(
        id=1,
        model_name="llama-2-7b-chat",
        version="2.0",
        format="GGUF",
        quantization="q4_0",
        context_length=4096,
        max_output=1024,
        hardware_profile="CPU/GPU",
        status="active"
    )


def list_model_profiles(db: Session) -> List[ModelProfile]:
    """List all model profiles."""
    db_models = db.query(models.ModelProfile).all()
    if not db_models:
        return [get_active_model_profile(db)]
    return [_to_dataclass(m) for m in db_models]


def stage_model_profile(
    db: Session,
    model_name: str,
    version: str,
    format: str = "GGUF",
    quantization: Optional[str] = "q4_0",
    context_length: int = 4096,
    max_output: int = 1024,
    hardware_profile: str = "CPU/GPU",
    checksum: Optional[str] = None,
    approval_id: Optional[str] = None,
) -> ModelProfile:
    """Stage a new model profile awaiting verification and promotion."""
    db_model = models.ModelProfile(
        model_name=model_name,
        version=version,
        format=format,
        quantization=quantization,
        context_length=context_length,
        max_output=max_output,
        hardware_profile=hardware_profile,
        checksum=checksum,
        approval_id=approval_id,
        status="staged"
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return _to_dataclass(db_model)


def activate_model_profile(db: Session, model_id: int) -> Optional[ModelProfile]:
    """
    Promote a model profile to active status and demote previously active profile.
    """
    target = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
    if not target:
        return None

    # Demote current active models to staged / deprecated
    db.query(models.ModelProfile).filter(
        models.ModelProfile.status == "active",
        models.ModelProfile.id != model_id
    ).update({"status": "staged"})

    target.status = "active"
    db.commit()
    db.refresh(target)
    logger.info(f"Model profile {target.model_name} (ID {target.id}) promoted to active.")
    return _to_dataclass(target)


def rollback_model_profile(db: Session, current_id: int) -> Optional[ModelProfile]:
    """Roll back from current active model to previous model."""
    target = db.query(models.ModelProfile).filter(
        models.ModelProfile.id != current_id
    ).order_by(models.ModelProfile.id.desc()).first()

    if target:
        return activate_model_profile(db, target.id)
    return None


def _to_dataclass(db_model: models.ModelProfile) -> ModelProfile:
    return ModelProfile(
        id=db_model.id,
        model_name=db_model.model_name,
        version=db_model.version,
        format=db_model.format,
        quantization=db_model.quantization,
        context_length=db_model.context_length or 4096,
        max_output=db_model.max_output or 1024,
        hardware_profile=db_model.hardware_profile or "CPU/GPU",
        checksum=db_model.checksum,
        approval_id=db_model.approval_id,
        status=db_model.status or "staged"
    )