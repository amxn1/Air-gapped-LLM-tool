"""
Vector store implementation using Qdrant with local in-memory fallback.
"""
import logging
import math
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


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
        Initialize the Qdrant client, with fallback to local in-memory store if Qdrant is unavailable.
        """
        self.host = host
        self.port = port
        self.collection_name = "document_chunks"
        self.vector_size = 384
        self._is_fallback = False
        self._in_memory_store = _SHARED_IN_MEMORY_STORE
        self.client = None

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import VectorParams, Distance
            self.client = QdrantClient(host=host, port=port, timeout=2.0)
            self._ensure_collection_exists()
        except Exception as e:
            logger.info(f"Qdrant server not reachable ({e}). Operating in resilient local in-memory mode.")
            self._is_fallback = True

    def _ensure_collection_exists(self):
        """Ensure the collection exists in Qdrant."""
        if self._is_fallback or not self.client:
            return
        try:
            from qdrant_client.http.models import VectorParams, Distance
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists.")
        except Exception:
            try:
                from qdrant_client.http.models import VectorParams, Distance
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
                logger.info(f"Collection '{self.collection_name}' created.")
            except Exception as e:
                logger.warning(f"Could not create Qdrant collection: {e}. Switching to in-memory fallback.")
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
                return
            except Exception as e:
                logger.warning(f"Qdrant add_vector failed: {e}. Storing in-memory.")
                self._is_fallback = True

        self._in_memory_store[str(vector_id)] = {
            "vector": vector,
            "payload": payload
        }

    def search_vectors(self, query_vector: List[float], limit: int = 5, collection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in the store."""
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
                return results
            except Exception as e:
                logger.warning(f"Qdrant search failed: {e}. Falling back to in-memory search.")
                self._is_fallback = True

        # In-memory search fallback
        scored = []
        for vid, item in self._in_memory_store.items():
            payload = item.get("payload", {})
            if collection_id is not None and payload.get("collection_id") != collection_id:
                continue
            sim = _cosine_similarity(query_vector, item.get("vector", []))
            scored.append({
                "id": vid,
                "score": sim,
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
            except Exception as e:
                logger.warning(f"Qdrant delete failed: {e}")

        self._in_memory_store.pop(str(vector_id), None)