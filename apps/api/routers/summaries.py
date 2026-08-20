import time
import uuid
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from packages.contracts.schemas import (
    SummaryRequest,
    SummaryResponse,
    RewritingRequest,
    RewritingResponse,
)
from ..services.llama_service import LlamaService
from ..database import get_db
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["summaries"],
)


@router.post("/summaries", response_model=SummaryResponse)
async def create_summary(request: SummaryRequest, db: Session = Depends(get_db)):
    """
    Create a summary of the provided content using specialized prompt templates.
    Supports quick, structured, long-document map-reduce, science-technology, and news-editorial.
    """
    llama_service = LlamaService()
    try:
        model_profile = None
        if request.model:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.model_name == request.model,
                models.ModelProfile.status == "active"
            ).first()

        if not model_profile:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.status == "active"
            ).first()

        model_id = model_profile.id if model_profile else None
        model_name = model_profile.model_name if model_profile else (request.model or "llama-2-7b-chat")
        VALID_SUMMARY_TYPES = {"quick", "structured", "long-document", "science-technology", "news-editorial"}
        summary_type = request.summary_type if request.summary_type in VALID_SUMMARY_TYPES else "structured"

        result = await llama_service.generate_summary(
            content=request.content,
            summary_type=summary_type,
            model_id=model_id,
            temperature=request.temperature or 0.3,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return SummaryResponse(
            id=str(uuid.uuid4()),
            summary=result.get("summary", ""),
            model_used=model_name,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary_type=summary_type,
            metadata={
                "summary_type": summary_type,
                "chunks_processed": result.get("chunks_processed", 1),
                "template": summary_type
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await llama_service.close()


@router.post("/rewrite", response_model=RewritingResponse)
async def rewrite_text(request: RewritingRequest, db: Session = Depends(get_db)):
    """
    Context-aware rewriting, grammar correction, and dialect/tone adaptation.
    Modes: formal, grammar, government, technical, plain_language, indian_english, uk_english, us_english.
    """
    llama_service = LlamaService()
    try:
        model_profile = None
        if request.model:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.model_name == request.model,
                models.ModelProfile.status == "active"
            ).first()

        if not model_profile:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.status == "active"
            ).first()

        model_id = model_profile.id if model_profile else None
        model_name = model_profile.model_name if model_profile else (request.model or "llama-2-7b-chat")

        result = await llama_service.generate_rewrite(
            text=request.text,
            mode=request.mode or "formal",
            model_id=model_id,
            temperature=request.temperature or 0.2
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return RewritingResponse(
            id=str(uuid.uuid4()),
            original_text=request.text,
            rewritten_text=result.get("rewritten_text", ""),
            changes_summary=f"Rewritten in mode: {request.mode}",
            mode=request.mode,
            model_used=model_name,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in rewrite_text: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await llama_service.close()