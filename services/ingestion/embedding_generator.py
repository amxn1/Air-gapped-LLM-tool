"""
Embedding generation for text chunks.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from ..inference.service import InferenceService
from ..inference.model_manager import get_active_model_profile

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for text chunks using a local inference service.
    """

    def __init__(self, db_session: Session, inference_service: Optional[InferenceService] = None):
        self.db = db_session
        self.inference_service = inference_service or InferenceService()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text string.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding
        """
        try:
            # Use the active model from the database
            embedding = await self.inference_service.embed_text(
                text=text,
                db=self.db,
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a zero vector as fallback
            # In a real implementation, you might want to raise or handle differently
            return [0.0] * 384  # Default embedding size

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    async def close(self):
        """Close the inference service."""
        await self.inference_service.close()