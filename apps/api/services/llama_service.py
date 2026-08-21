"""
Service for interacting with model inference and task orchestration.
"""
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from packages.prompts.manager import default_prompt_manager
from services.inference.service import InferenceService
from services.inference.model_manager import get_active_model_profile, get_model_profile
from apps.api.database import SessionLocal
from services.ingestion.chunker import chunk_by_paragraphs

logger = logging.getLogger(__name__)


class LlamaService:
    """
    Service layer for model inference and prompt template coordination.
    """

    def __init__(self):
        self.db = SessionLocal()
        self.inference_service = InferenceService()
        self.prompt_manager = default_prompt_manager

    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        task_mode: Optional[str] = "chat",
        system_override: Optional[str] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate a chat response from a list of messages.
        """
        try:
            # Build structured prompt using PromptManager
            prompt = self.prompt_manager.build_chat_prompt(messages, system_override=system_override)

            response = await self.inference_service.generate_text(
                prompt=prompt,
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens or 1024,
                stream=stream,
                db=self.db,
                messages=messages,
            )
            return response
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            if stream:
                async def error_stream():
                    yield {"error": str(e)}
                return error_stream()
            return {"error": str(e)}

    async def generate_summary(
        self,
        content: str,
        summary_type: str = "structured",
        model_id: Optional[int] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate a summary using specialized task templates.
        """
        try:
            model_profile = get_model_profile(self.db, model_id) if model_id else get_active_model_profile(self.db)
            active_model_id = model_profile.id if model_profile else None
            model_name = model_profile.model_name if model_profile else "llama-2-7b-chat"

            # Handle large documents with map-reduce
            if summary_type in ["long-document", "science-technology", "news-editorial"] and len(content) > 3500:
                return await self._generate_long_document_summary(
                    content=content,
                    model_id=active_model_id,
                    temperature=temperature,
                    summary_type=summary_type
                )

            # Build prompt using PromptManager
            prompt_data = self.prompt_manager.build_summary_prompt(content, summary_type=summary_type)
            full_prompt = f"system: {prompt_data['system_prompt']}\n\nuser: {prompt_data['user_prompt']}\n\nassistant: "

            params = prompt_data.get("parameters", {})
            max_tokens = params.get("max_tokens", 768)

            response = await self.inference_service.generate_text(
                prompt=full_prompt,
                model_id=active_model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                db=self.db
            )

            return {
                "summary": response.get("content", ""),
                "model_used": model_name,
                "summary_type": summary_type,
                "model_id": active_model_id
            }
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {"error": str(e)}

    async def generate_rewrite(
        self,
        text: str,
        mode: str = "formal",
        model_id: Optional[int] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate context-aware rewriting and grammar correction.
        """
        try:
            model_profile = get_model_profile(self.db, model_id) if model_id else get_active_model_profile(self.db)
            active_model_id = model_profile.id if model_profile else None
            model_name = model_profile.model_name if model_profile else "llama-2-7b-chat"

            prompt_data = self.prompt_manager.build_rewriting_prompt(text, mode=mode)
            full_prompt = f"system: {prompt_data['system_prompt']}\n\nuser: {prompt_data['user_prompt']}\n\nassistant: "

            response = await self.inference_service.generate_text(
                prompt=full_prompt,
                model_id=active_model_id,
                temperature=temperature,
                max_tokens=1024,
                stream=False,
                db=self.db
            )

            raw_content = response.get("content", "")
            return {
                "rewritten_text": raw_content,
                "original_text": text,
                "mode": mode,
                "model_used": model_name,
                "model_id": active_model_id
            }
        except Exception as e:
            logger.error(f"Error in generate_rewrite: {e}")
            return {"error": str(e)}

    async def _generate_long_document_summary(
        self,
        content: str,
        model_id: Optional[int],
        temperature: float,
        summary_type: str
    ) -> Dict[str, Any]:
        """Map-reduce summarization for large text chunks."""
        chunks = chunk_by_paragraphs(content, max_chunk_size=1800, overlap_sentences=1)
        if not chunks:
            return {"error": "Failed to chunk the long document"}

        template = self.prompt_manager.get_template("long_document_map_reduce")
        map_system = template.get("map_system_prompt", "Summarize this section.") if template else "Summarize."
        map_tmpl = template.get("map_user_template", "{chunk_text}") if template else "{chunk_text}"

        chunk_summaries = []
        for i, c in enumerate(chunks):
            user_msg = map_tmpl.format(section_info=f"Section {i+1}", chunk_text=c["text"])
            prompt = f"system: {map_system}\n\nuser: {user_msg}\n\nassistant: "

            res = await self.inference_service.generate_text(
                prompt=prompt,
                model_id=model_id,
                temperature=temperature,
                max_tokens=256,
                stream=False,
                db=self.db
            )
            s_text = res.get("content", "").strip()
            if s_text:
                chunk_summaries.append(f"- Section {i+1}: {s_text}")

        # Reduce phase
        combined_summaries = "\n".join(chunk_summaries)
        reduce_system = template.get("reduce_system_prompt", "Synthesize all section summaries.") if template else "Synthesize."
        reduce_tmpl = template.get("reduce_user_template", "{section_summaries}") if template else "{section_summaries}"
        final_user = reduce_tmpl.format(section_summaries=combined_summaries)

        final_prompt = f"system: {reduce_system}\n\nuser: {final_user}\n\nassistant: "
        final_res = await self.inference_service.generate_text(
            prompt=final_prompt,
            model_id=model_id,
            temperature=temperature,
            max_tokens=1024,
            stream=False,
            db=self.db
        )

        model_profile = get_model_profile(self.db, model_id) if model_id else get_active_model_profile(self.db)
        return {
            "summary": final_res.get("content", ""),
            "model_used": model_profile.model_name if model_profile else "llama-2-7b-chat",
            "summary_type": summary_type,
            "model_id": model_id,
            "chunks_processed": len(chunk_summaries)
        }

    async def close(self):
        await self.inference_service.close()
        self.db.close()