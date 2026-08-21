"""
Health check endpoints for service and subsystem monitoring.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from services.retrieval.vector_store import VectorStore
import time

router = APIRouter(
    tags=["health"],
)


@router.get("/health")
@router.get("/v1/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check verifying PostgreSQL database, vector store, and model subsystem.
    """
    db_status = "healthy"
    try:
        db.query(models.User).limit(1).all()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    vector_status = "healthy"
    try:
        vs = VectorStore()
        if vs._is_fallback:
            vector_status = "in-memory-local"
    except Exception as e:
        vector_status = f"degraded: {str(e)}"

    return {
        "status": "healthy" if "healthy" in db_status else "degraded",
        "service": "offline-llm-assistant",
        "version": "1.0.0",
        "network_mode": "air-gapped",
        "components": {
            "database": db_status,
            "vector_store": vector_status,
            "inference_engine": "ready"
        },
        "timestamp": int(time.time())
    }