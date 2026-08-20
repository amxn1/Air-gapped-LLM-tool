"""
Main FastAPI application for the Offline LLM Assistant.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .database import engine, Base
from . import models

# Import routers
from .routers import health, models as models_router, chat, summaries, documents, collections, admin
from .auth import router as auth_router

# Import middleware
from .middleware.audit import AuditMiddleware

# Initialize database schema if not present
try:
    Base.metadata.create_all(bind=engine)
except Exception as db_init_err:
    pass

# Create FastAPI app instance
app = FastAPI(
    title="Offline LLM Assistant",
    description="A fully air-gapped, on-premises assistant for secure natural language processing",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add audit middleware
app.add_middleware(AuditMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(models_router.router)
app.include_router(chat.router)
app.include_router(summaries.router)
app.include_router(documents.router)
app.include_router(collections.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Root endpoint returning basic service information."""
    return {
        "service": "Offline LLM Assistant",
        "version": "1.0.0",
        "status": "running",
        "network_mode": "air-gapped",
        "description": "Air-gapped LLM assistant for secure natural language processing",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)