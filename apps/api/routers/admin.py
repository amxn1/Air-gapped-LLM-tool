"""
Administration endpoints for user management, audit review, and system telemetry.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.contracts.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    AuditEventResponse,
    SystemStatsResponse,
)
from .. import models
from ..database import get_db
from ..auth import crud as auth_crud

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
)


# User Management Endpoints
@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all users with pagination."""
    users = auth_crud.get_users(db, skip=skip, limit=limit)
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    """Create a new user."""
    db_user = auth_crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    db_user_email = auth_crud.get_user_by_email(db, user.email)
    if db_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Convert UserCreate to auth schemas
    from ..auth import schemas as auth_schemas
    auth_user = auth_schemas.UserCreate(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password=user.password
    )
    created_user = auth_crud.create_user(db, auth_user)
    if user.role:
        created_user.role = user.role
        db.commit()
        db.refresh(created_user)
    return created_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific user by ID."""
    db_user = auth_crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
):
    """Update a user's details or role."""
    from ..auth import schemas as auth_schemas
    auth_update = auth_schemas.UserUpdate(
        email=user_update.email,
        full_name=user_update.full_name,
        password=user_update.password,
        is_active=user_update.is_active,
        role=user_update.role
    )
    db_user = auth_crud.update_user(db, user_id=user_id, user_update=auth_update)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Delete a user."""
    db_user = auth_crud.delete_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return None


# Audit Events Explorer
@router.get("/audit/events", response_model=List[AuditEventResponse])
def list_audit_events(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    actor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Query immutable audit events for security review."""
    query = db.query(models.AuditEvent)
    if action:
        query = query.filter(models.AuditEvent.action == action)
    if actor_id:
        query = query.filter(models.AuditEvent.actor_id == actor_id)

    events = query.order_by(models.AuditEvent.timestamp.desc()).offset(skip).limit(limit).all()
    return events


# System Statistics Endpoint
@router.get("/stats", response_model=SystemStatsResponse)
def get_system_stats(
    db: Session = Depends(get_db),
):
    """Get system telemetry and resource counts."""
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()

    total_documents = db.query(models.Document).count()
    completed_documents = db.query(models.Document).filter(models.Document.import_status == "completed").count()

    total_collections = db.query(models.Collection).count()
    active_collections = db.query(models.Collection).filter(models.Collection.is_active == True).count()

    total_conversations = db.query(models.Conversation).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users
        },
        "documents": {
            "total": total_documents,
            "completed": completed_documents,
            "processing": db.query(models.Document).filter(models.Document.import_status == "processing").count(),
            "failed": db.query(models.Document).filter(models.Document.import_status == "failed").count(),
            "pending": db.query(models.Document).filter(models.Document.import_status == "pending").count()
        },
        "collections": {
            "total": total_collections,
            "active": active_collections,
            "inactive": total_collections - active_collections
        },
        "conversations": {
            "total": total_conversations
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Role Management Endpoints
@router.get("/roles")
def get_available_roles():
    """Get list of system roles with permission matrix."""
    return {
        "roles": [
            {"value": "admin", "label": "System Administrator", "description": "Full access to infrastructure, models, users, and audit logs"},
            {"value": "model_operator", "label": "Model Operator", "description": "Stage, test, activate, and rollback approved model profiles"},
            {"value": "collection_steward", "label": "Collection Steward", "description": "Manage document collections and access rules"},
            {"value": "security_auditor", "label": "Security Auditor", "description": "Review immutable audit events and policy logs"},
            {"value": "user", "label": "Standard User", "description": "Chat, summarize, rewrite, and query authorized collections"}
        ]
    }


@router.get("/config")
def get_system_config():
    """Get current air-gapped system operational limits and features."""
    return {
        "network_mode": "air-gapped",
        "external_egress": "disabled",
        "features": {
            "chat_completions": True,
            "rag_citations": True,
            "multi_mode_summaries": True,
            "rewriting_grammar": True,
            "document_management": True,
            "model_registry": True,
            "audit_logging": True
        },
        "limits": {
            "max_upload_size_mb": 100,
            "default_context_tokens": 4096,
            "max_output_tokens": 2048
        },
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }