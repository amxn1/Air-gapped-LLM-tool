"""
Retrieval service for finding relevant document chunks and assembling citations.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .vector_store import VectorStore
from ..inference.service import InferenceService
from apps.api import models

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Service for retrieving relevant document chunks with RBAC policy enforcement.
    """

    def __init__(self, db_session: Session, vector_store: Optional[VectorStore] = None):
        self.db = db_session
        self.vector_store = vector_store or VectorStore()
        self.inference_service = InferenceService()

    async def retrieve_relevant_chunks(
        self,
        query: str,
        limit: int = 5,
        collection_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_role: Optional[str] = "user"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks with authorization and collection filtering.

        Args:
            query: The query text to search for.
            limit: Maximum number of chunks to return.
            collection_id: Optional collection filter.
            user_id: ID of the querying user.
            user_role: Role of the querying user.

        Returns:
            List of dictionaries containing chunk text, source filename, page/section, and metadata.
        """
        try:
            # 1. Pre-retrieval Authorization: Check collection access if collection_id provided
            if collection_id is not None:
                collection = self.db.query(models.Collection).filter(
                    models.Collection.id == collection_id,
                    models.Collection.is_active == True
                ).first()

                if not collection:
                    logger.warning(f"Collection {collection_id} not found or inactive")
                    return []

                # Role-based policy check
                if collection.access_policy == "admin_only" and user_role != "admin":
                    logger.warning(f"User {user_id} denied access to admin_only collection {collection_id}")
                    return []

            # 2. Generate embedding for query
            query_embedding = await self.inference_service.embed_text(
                text=query,
                db=self.db
            )

            # 3. Search vector store
            search_results = self.vector_store.search_vectors(
                query_vector=query_embedding,
                limit=limit,
                collection_id=collection_id
            )

            # 4. Assemble chunks with database metadata & citations
            chunks = []
            for result in search_results:
                payload = result.get("payload", {})
                doc_id = payload.get("document_id")
                chunk_id = payload.get("chunk_id")

                # Fetch document details from relational DB for provenance
                doc = None
                if doc_id:
                    doc = self.db.query(models.Document).filter(models.Document.id == doc_id).first()

                # Pre-retrieval access check: if user is not owner and not admin and collection is restricted
                if doc and user_id and user_role != "admin":
                    if doc.collection and doc.collection.access_policy == "admin_only":
                        continue

                filename = doc.original_filename if doc else payload.get("filename", f"Document_{doc_id}")
                page_or_section = payload.get("page_or_section", f"Chunk {chunk_id}")

                chunk_info = {
                    "text": payload.get("text", ""),
                    "document_id": doc_id,
                    "chunk_id": chunk_id,
                    "filename": filename,
                    "page_or_section": page_or_section,
                    "score": round(float(result.get("score", 0.0)), 4)
                }
                chunks.append(chunk_info)

            return chunks

        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {e}", exc_info=True)
            return []

    async def close(self):
        """Close the inference service."""
        await self.inference_service.close()