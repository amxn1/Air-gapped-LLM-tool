from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import shutil
from pathlib import Path
import uuid
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from pydantic import BaseModel

from packages.contracts.schemas import DocumentResponse, DocumentChunkResponse
from ..database import get_db
from services.ingestion.worker import IngestionWorker
from services.retrieval.vector_store import VectorStore
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/documents",
    tags=["documents"],
)

STORAGE_DIR = Path("./storage")
STORAGE_DIR.mkdir(exist_ok=True)

UPLOAD_DIR = Path("./uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)


class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    collection_id: Optional[int] = None


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: int = 1,
    collection_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a document and trigger offline ingestion pipeline (TXT, MD, PDF, DOCX, HTML).
    """
    allowed_extensions = {
        ".txt", ".pdf", ".docx", ".doc", ".md", ".markdown", ".html", ".htm",
        ".json", ".jsonl", ".csv", ".tsv", ".py", ".js", ".ts", ".jsx", ".tsx",
        ".log", ".yaml", ".yml", ".ini", ".env", ".sql", ".sh", ".c", ".cpp", ".h"
    }
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_extension}'. Supported: PDF, Word, Markdown, Text, Code, CSV, JSON."
        )

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    temp_file_path = UPLOAD_DIR / unique_filename
    perm_file_path = STORAGE_DIR / unique_filename

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        shutil.copy2(temp_file_path, perm_file_path)

        worker = IngestionWorker(db_session=db)
        result = worker.process_file(
            file_path=perm_file_path,
            user_id=user_id,
            collection_id=collection_id
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {result.get('errors', ['Unknown error'])}"
            )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Document uploaded and processed successfully",
                "document_id": result["document_id"],
                "filename": file.filename,
                "chunks_created": result["chunks_created"],
                "extracted_text": result.get("extracted_text", ""),
                "preview": result.get("preview", ""),
                "total_pages": result.get("total_pages", 1),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document {file.filename}: {e}")
        if perm_file_path.exists():
            try:
                perm_file_path.unlink()
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )
    finally:
        try:
            if temp_file_path.exists():
                temp_file_path.unlink()
        except Exception:
            pass


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    collection_id: Optional[int] = None,
    import_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user_id: int = 1
):
    """
    List documents with optional filtering.
    """
    query = db.query(models.Document)

    if collection_id is not None:
        query = query.filter(models.Document.collection_id == collection_id)

    if import_status is not None:
        query = query.filter(models.Document.import_status == import_status)

    documents = query.offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific document by ID.
    """
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document: DocumentUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a document's metadata.
    """
    db_document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.collection_id is not None:
        collection = db.query(models.Collection).filter(
            models.Collection.id == document.collection_id,
            models.Collection.is_active == True
        ).first()
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid collection ID"
            )

    update_data = document.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_document, field, value)

    db.commit()
    db.refresh(db_document)
    return db_document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a document, its database chunks, physical storage, and vector embeddings.
    """
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Fetch chunk IDs for vector store deletion
    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).all()

    vector_store = VectorStore()
    for c in chunks:
        try:
            vector_store.delete_vector(str(c.id))
        except Exception as e:
            logger.warning(f"Error removing vector for chunk {c.id}: {e}")

    # Delete chunks from database
    db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).delete()

    # Delete physical file from disk if present
    if document.file_path and Path(document.file_path).exists():
        try:
            Path(document.file_path).unlink()
        except Exception as e:
            logger.warning(f"Could not delete physical file {document.file_path}: {e}")

    # Delete document record
    db.delete(document)
    db.commit()
    return None


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Get chunks for a specific document.
    """
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).order_by(models.DocumentChunk.chunk_index).all()
    return chunks


@router.get("/{document_id}/content")
def get_document_content(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Get full extracted text and chunk summaries for a specific document.
    """
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document_id
    ).order_by(models.DocumentChunk.chunk_index).all()

    full_text = "\n\n".join([c.text for c in chunks if c.text])
    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "media_type": document.media_type,
        "import_status": document.import_status,
        "chunks_count": len(chunks),
        "content": full_text
    }


@router.get("/{document_id}/download")
def download_document_file(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Download the original uploaded document file.
    """
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.file_path or not Path(document.file_path).exists():
        raise HTTPException(status_code=404, detail="Physical file not found on disk")

    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.media_type
    )