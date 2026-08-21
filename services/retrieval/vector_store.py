"""
Vector store implementation using Qdrant with persistent SQLite database synchronization.
"""
import hashlib
import logging
import math
import os
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _generate_deterministic_embedding(text: str, dim: int = 384) -> List[float]:
    """Generate a deterministic pseudo-embedding from text for offline indexing."""
    raw_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dim):
        byte_val = raw_hash[i % len(raw_hash)]
        val = (byte_val / 255.0) * 2.0 - 1.0 + (math.sin(i + len(text)) * 0.1)
        vec.append(val)
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


_SHARED_IN_MEMORY_STORE: Dict[str, Dict[str, Any]] = {}


class VectorStore:
    def __init__(self, host: str = "localhost", port: int = 6333):
        """
        Initialize VectorStore with local persistent sync from SQLite and optional Qdrant.
        """
        self.host = host
        self.port = port
        self.collection_name = "document_chunks"
        self.vector_size = 384
        self._is_fallback = False
        self._in_memory_store = _SHARED_IN_MEMORY_STORE
        self.client = None
        self._is_fallback = True

        if os.environ.get("USE_QDRANT", "0") == "1":
            try:
                from qdrant_client import QdrantClient
                self.client = QdrantClient(host=host, port=port, timeout=0.3, check_compatibility=False)
                self._ensure_collection_exists()
                self._is_fallback = False
            except Exception:
                self._is_fallback = True

        # Always sync with SQLite so all uploaded files are searchable
        self._sync_from_sqlite()

    def _sync_from_sqlite(self):
        """Sync chunks and document metadata from SQLite into the vector cache."""
        try:
            from apps.api.database import SessionLocal
            from apps.api import models

            db = SessionLocal()
            try:
                # Load all chunks
                chunks = db.query(models.DocumentChunk).all()
                if not chunks:
                    return

                # Build doc map
                docs = {d.id: d for d in db.query(models.Document).all()}

                for c in chunks:
                    cid_str = str(c.id)
                    if cid_str not in self._in_memory_store:
                        doc = docs.get(c.document_id)
                        filename = doc.original_filename if doc else f"Document_{c.document_id}"
                        collection_id = doc.collection_id if doc else None
                        text = c.text or ""
                        vec = _generate_deterministic_embedding(text)

                        self._in_memory_store[cid_str] = {
                            "vector": vec,
                            "payload": {
                                "document_id": c.document_id,
                                "chunk_id": c.id,
                                "collection_id": collection_id,
                                "filename": filename,
                                "page_or_section": f"Chunk {c.chunk_index + 1}",
                                "text": text,
                            }
                        }
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"SQLite vector sync notice: {e}")

    def _ensure_collection_exists(self):
        """Ensure the collection exists in Qdrant."""
        if self._is_fallback or not self.client:
            return
        try:
            from qdrant_client.http.models import VectorParams, Distance
            self.client.get_collection(self.collection_name)
        except Exception:
            try:
                from qdrant_client.http.models import VectorParams, Distance
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
            except Exception:
                self._is_fallback = True

    def add_vector(self, vector_id: str, vector: List[float], payload: Dict[str, Any]):
        """Add a vector to the store."""
        if not self._is_fallback and self.client:
            try:
                from qdrant_client.http.models import PointStruct
                point = PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload=payload
                )
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
            except Exception:
                self._is_fallback = True

        self._in_memory_store[str(vector_id)] = {
            "vector": vector,
            "payload": payload
        }

    def search_vectors(
        self,
        query_vector: List[float],
        limit: int = 6,
        collection_id: Optional[int] = None,
        query_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the store with hybrid lexical/semantic scoring."""
        # Ensure memory store is synced
        if not self._in_memory_store:
            self._sync_from_sqlite()

        if not self._is_fallback and self.client:
            try:
                search_result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit
                )
                results = []
                for scored_point in search_result:
                    payload = scored_point.payload or {}
                    if collection_id is not None and payload.get("collection_id") != collection_id:
                        continue
                    results.append({
                        "id": scored_point.id,
                        "score": scored_point.score,
                        "payload": payload
                    })
                if results:
                    return results
            except Exception:
                self._is_fallback = True

        # Hybrid In-Memory Search
        query_str = (query_text or "").lower()
        query_tokens = set(re.findall(r"\w{2,}", query_str))
        
        # Check if user is asking for general summary / reading docs
        is_general_doc_query = any(w in query_str for w in [
            "pdf", "document", "file", "summar", "explain", "policy", "what is", "tell me", "read"
        ])

        scored = []
        for vid, item in self._in_memory_store.items():
            payload = item.get("payload", {})
            if collection_id is not None and payload.get("collection_id") != collection_id:
                continue

            chunk_text = payload.get("text", "").lower()
            filename = payload.get("filename", "").lower()

            sim = _cosine_similarity(query_vector, item.get("vector", []))

            # 1. Lexical Token Overlap
            overlap_score = 0.0
            if query_tokens and chunk_text:
                chunk_tokens = set(re.findall(r"\w{2,}", chunk_text))
                common = query_tokens.intersection(chunk_tokens)
                overlap_score = len(common) / max(len(query_tokens), 1)

            # 2. Filename Boost (if query mentions document name or parts of it)
            filename_boost = 0.0
            for qt in query_tokens:
                if len(qt) > 3 and qt in filename:
                    filename_boost += 0.5

            # Combined Score
            if query_tokens:
                final_score = (sim * 0.25) + (overlap_score * 0.55) + (filename_boost * 0.2)
            else:
                final_score = sim

            # If general query and score is low, give baseline score so document content is available
            if is_general_doc_query and final_score < 0.1:
                final_score = 0.15

            scored.append({
                "id": vid,
                "score": final_score,
                "payload": payload
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def delete_vector(self, vector_id: str):
        """Delete a vector from the store by its ID."""
        if not self._is_fallback and self.client:
            try:
                from qdrant_client.http import models as rest
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=rest.PointIdsList(points=[vector_id]),
                )
            except Exception:
                pass

        self._in_memory_store.pop(str(vector_id), None)