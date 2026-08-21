"""
Fast, robust embedding generation for text chunks.
"""
import logging
from typing import List, Optional, Any

from sqlalchemy.orm import Session
from services.retrieval.vector_store import _generate_deterministic_embedding

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for text chunks using deterministic fast offline embeddings.
    """

    def __init__(self, db_session: Optional[Session] = None, inference_service: Optional[Any] = None):
        self.db = db_session

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding for a single text string."""
        return _generate_deterministic_embedding(text, dim=384)

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts in milliseconds."""
        return [_generate_deterministic_embedding(t, dim=384) for t in texts]

    async def close(self):
        """Cleanup resources."""
        pass