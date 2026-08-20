"""
Collection management endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.contracts.schemas import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    DocumentResponse,
)
from ..database import get_db
from .. import models

router = APIRouter(
    prefix="/v1/collections",
    tags=["collections"],
)


@router.get("/", response_model=List[CollectionResponse])
def list_collections(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all active collections."""
    collections = db.query(models.Collection).filter(
        models.Collection.is_active == True
    ).offset(skip).limit(limit).all()
    return collections


@router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    collection: CollectionCreate,
    db: Session = Depends(get_db),
):
    """Create a new collection."""
    db_collection = models.Collection(
        name=collection.name,
        description=collection.description,
        classification=collection.classification or "internal",
        access_policy=collection.access_policy or "authenticated",
        owner_id=1
    )
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific collection by ID."""
    collection = db.query(models.Collection).filter(
        models.Collection.id == collection_id
    ).first()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    collection: CollectionUpdate,
    db: Session = Depends(get_db),
):
    """Update a collection."""
    db_collection = db.query(models.Collection).filter(
        models.Collection.id == collection_id
    ).first()
    if db_collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    update_data = collection.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_collection, field, value)

    db.commit()
    db.refresh(db_collection)
    return db_collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db),
):
    """Soft delete a collection."""
    collection = db.query(models.Collection).filter(
        models.Collection.id == collection_id
    ).first()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection.is_active = False
    db.commit()
    return None


@router.get("/{collection_id}/documents", response_model=List[DocumentResponse])
def get_collection_documents(
    collection_id: int,
    db: Session = Depends(get_db),
):
    """Get all documents in a collection."""
    collection = db.query(models.Collection).filter(
        models.Collection.id == collection_id
    ).first()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    documents = db.query(models.Document).filter(
        models.Document.collection_id == collection_id
    ).all()
    return documents