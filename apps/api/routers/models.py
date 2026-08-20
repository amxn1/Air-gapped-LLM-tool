"""
Model registry management endpoints.
"""
import time
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.contracts.schemas import (
    ModelProfileCreate,
    ModelProfileResponse,
    ModelActivationRequest,
)
from ..database import get_db
from .. import models
from services.inference.model_manager import (
    stage_model_profile,
    activate_model_profile,
    rollback_model_profile,
    get_active_model_profile,
)
from ..services.llama_service import LlamaService

router = APIRouter(
    prefix="/v1/models",
    tags=["models"],
)


@router.get("", response_model=List[ModelProfileResponse])
def get_models(db: Session = Depends(get_db)):
    """Return a list of all model profiles in the registry."""
    profiles = db.query(models.ModelProfile).all()
    if not profiles:
        # Seed default profile if empty
        default_model = models.ModelProfile(
            model_name="llama-2-7b-chat",
            version="2.0",
            format="GGUF",
            quantization="q4_0",
            context_length=4096,
            max_output=1024,
            hardware_profile="CPU/GPU",
            status="active"
        )
        db.add(default_model)
        db.commit()
        db.refresh(default_model)
        profiles = [default_model]
    return profiles


@router.get("/{model_id}", response_model=ModelProfileResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    """Get a specific model profile."""
    profile = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Model profile not found")
    return profile


@router.post("/stage", response_model=ModelProfileResponse, status_code=status.HTTP_201_CREATED)
def stage_model(profile_in: ModelProfileCreate, db: Session = Depends(get_db)):
    """Stage a newly imported offline model artifact."""
    profile = stage_model_profile(
        db=db,
        model_name=profile_in.model_name,
        version=profile_in.version,
        format=profile_in.format,
        quantization=profile_in.quantization,
        context_length=profile_in.context_length,
        max_output=profile_in.max_output,
        hardware_profile=profile_in.hardware_profile or "CPU/GPU",
        checksum=profile_in.checksum,
        approval_id=profile_in.approval_id
    )
    db_obj = db.query(models.ModelProfile).filter(models.ModelProfile.id == profile.id).first()
    return db_obj


@router.post("/{model_id}/activate", response_model=ModelProfileResponse)
def activate_model(model_id: int, db: Session = Depends(get_db)):
    """Promote a staged model to active status for inference."""
    profile = activate_model_profile(db, model_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Model profile not found")
    db_obj = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
    return db_obj


@router.post("/{model_id}/rollback", response_model=ModelProfileResponse)
def rollback_model(model_id: int, db: Session = Depends(get_db)):
    """Roll back to previous active model profile."""
    profile = rollback_model_profile(db, model_id)
    if not profile:
        raise HTTPException(status_code=400, detail="No previous model profile available for rollback")
    db_obj = db.query(models.ModelProfile).filter(models.ModelProfile.id == profile.id).first()
    return db_obj


@router.post("/{model_id}/test")
async def smoke_test_model(model_id: int, db: Session = Depends(get_db)):
    """Run a local smoke test on a model profile to verify execution and measure latency."""
    profile = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Model profile not found")

    llama_service = LlamaService()
    start_time = time.time()
    try:
        res = await llama_service.generate_chat_response(
            messages=[{"role": "user", "content": "Smoke test diagnostic ping."}],
            model_id=model_id,
            max_tokens=32,
            stream=False
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "passed",
            "model_name": profile.model_name,
            "version": profile.version,
            "latency_ms": elapsed_ms,
            "output_sample": res.get("content", "")[:100] if isinstance(res, dict) else "OK"
        }
    except Exception as e:
        return {
            "status": "failed",
            "model_name": profile.model_name,
            "error": str(e)
        }
    finally:
        await llama_service.close()