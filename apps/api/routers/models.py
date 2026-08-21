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
import httpx
from ..services.llama_service import LlamaService

router = APIRouter(
    prefix="/v1/models",
    tags=["models"],
)


@router.get("/status")
async def get_models_status(db: Session = Depends(get_db)):
    """Return live status of Ollama connection and installed models."""
    ollama_online = False
    installed_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get("http://127.0.0.1:11434/api/tags")
            if res.status_code == 200:
                ollama_online = True
                installed_models = [m.get("name") for m in res.json().get("models", []) if m.get("name")]
    except Exception:
        pass

    active_profile = db.query(models.ModelProfile).filter(models.ModelProfile.status == "active").first()
    active_name = active_profile.model_name if active_profile else (installed_models[0] if installed_models else "llama3.2:1b")

    return {
        "ollama_online": ollama_online,
        "ollama_url": "http://127.0.0.1:11434",
        "installed_models": installed_models,
        "active_model": active_name,
        "recommended_model": "llama3.2:1b",
    }


@router.get("", response_model=List[ModelProfileResponse])
async def get_models(db: Session = Depends(get_db)):
    """Return a list of all model profiles in the registry with live Ollama detection."""
    # Detect live Ollama models
    installed_names = set()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get("http://127.0.0.1:11434/api/tags")
            if res.status_code == 200:
                for m in res.json().get("models", []):
                    if m.get("name"):
                        installed_names.add(m.get("name"))
    except Exception:
        pass

    profiles = db.query(models.ModelProfile).all()
    if not profiles:
        # Seed default profile if empty
        default_model = models.ModelProfile(
            model_name="llama3.2:1b",
            version="3.2",
            format="Ollama / GGUF",
            quantization="q4_K_M",
            context_length=128000,
            max_output=4096,
            hardware_profile="CPU/GPU",
            status="active"
        )
        db.add(default_model)
        db.commit()
        db.refresh(default_model)
        profiles = [default_model]

    # Ensure llama3.2:1b exists in DB
    has_llama1b = any(p.model_name == "llama3.2:1b" for p in profiles)
    if not has_llama1b and "llama3.2:1b" in installed_names:
        new_prof = models.ModelProfile(
            model_name="llama3.2:1b",
            version="3.2",
            format="Ollama / GGUF",
            quantization="q4_K_M",
            context_length=128000,
            max_output=4096,
            hardware_profile="CPU/GPU",
            status="active"
        )
        db.add(new_prof)
        db.commit()
        db.refresh(new_prof)
        profiles.append(new_prof)

    # Sort installed models (and llama3.2:1b) first
    def sort_key(p):
        is_installed = p.model_name in installed_names or "llama3.2:1b" in p.model_name
        is_active = p.status == "active"
        return (0 if is_installed else 1, 0 if is_active else 1, p.id)

    profiles.sort(key=sort_key)
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