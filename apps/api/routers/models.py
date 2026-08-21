"""
Model registry management endpoints.
"""
import time
from typing import List, Dict, Any, Optional
import httpx
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


async def _sync_ollama_models(db: Session):
    """Auto-discover locally installed models in Ollama daemon and synchronize."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get("http://localhost:11434/api/tags")
            if res.status_code == 200:
                ollama_models = res.json().get("models", [])
                installed_names = set()
                for om in ollama_models:
                    m_name = om.get("name")
                    if not m_name:
                        continue
                    installed_names.add(m_name)
                    existing = db.query(models.ModelProfile).filter(models.ModelProfile.model_name == m_name).first()
                    if not existing:
                        details = om.get("details", {})
                        new_profile = models.ModelProfile(
                            model_name=m_name,
                            version="1.0",
                            format=str(details.get("format", "GGUF")).upper(),
                            quantization=str(details.get("quantization_level", "q4_k_m")),
                            context_length=8192,
                            max_output=2048,
                            hardware_profile="Ollama Local",
                            status="active"
                        )
                        db.add(new_profile)
                    else:
                        existing.status = "active"

                # Remove any stale staged models that do not exist locally
                for db_model in db.query(models.ModelProfile).all():
                    if db_model.model_name not in installed_names and db_model.hardware_profile == "Ollama Local":
                        db.delete(db_model)

                db.commit()
    except Exception:
        pass


@router.get("", response_model=List[ModelProfileResponse])
async def get_models(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Return a list of available model profiles in the registry."""
    await _sync_ollama_models(db)
    query = db.query(models.ModelProfile)
    if status:
        query = query.filter(models.ModelProfile.status == status)
    profiles = query.all()
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
    db_obj = db.query(models.ModelProfile).filter(models.ModelProfile.id == model_id).first()
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