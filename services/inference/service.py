"""
Inference service that orchestrates model inference.
"""
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .adapters.llama_cpp import LlamaCppAdapter
from .model_manager import ModelProfile, get_active_model_profile, get_model_profile

logger = logging.getLogger(__name__)


class InferenceService:
    """
    Service for handling inference requests.
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.adapter = LlamaCppAdapter(base_url=base_url)

    async def generate_text(
        self,
        prompt: str,
        model_id: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        db: Optional[Session] = None,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate text using the specified model.

        Args:
            prompt: The input prompt
            model_id: The ID of the model profile to use. If None, uses the active model.
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop: List of stop sequences
            stream: Whether to stream the response
            db: Database session (required if model_id is None to fetch active model)
            messages: Optional structured chat message history

        Returns:
            Either a dict with the full response or an async generator for streaming
        """
        # Determine which model to use
        if model_id is not None:
            if db is None:
                raise ValueError("Database session is required when specifying model_id")
            model_profile = get_model_profile(db, model_id)
            if model_profile is None:
                raise ValueError(f"Model with ID {model_id} not found")
        else:
            model_profile = get_active_model_profile(db) if db else None
            if model_profile is None:
                raise ValueError("No active model profile found. Please activate a model first.")

        logger.info(
            f"Generating text with model {model_profile.model_name} (ID: {model_profile.id})"
        )

        # Generate the response
        return await self.adapter.generate(
            prompt=prompt,
            model_profile=model_profile,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
            stream=stream,
            messages=messages,
        )

    async def embed_text(
        self, text: str, model_id: Optional[int] = None, db: Optional[Session] = None
    ) -> List[float]:
        """
        Generate embeddings for text using the specified model.

        Args:
            text: The input text
            model_id: The ID of the model profile to use. If None, uses the active model.
            db: Database session (required if model_id is None to fetch active model)

        Returns:
            List of floats representing the embedding
        """
        # Determine which model to use
        if model_id is not None:
            if db is None:
                raise ValueError("Database session is required when specifying model_id")
            model_profile = get_model_profile(db, model_id)
            if model_profile is None:
                raise ValueError(f"Model with ID {model_id} not found")
        else:
            model_profile = get_active_model_profile(db) if db else None
            if model_profile is None:
                raise ValueError("No active model profile found. Please activate a model first.")

        logger.info(f"Generating embedding with model {model_profile.model_name}")

        # Generate the embedding
        return await self.adapter.embed(text=text, model_profile=model_profile)

    async def close(self):
        """Close the adapter and clean up resources."""
        await self.adapter.close()