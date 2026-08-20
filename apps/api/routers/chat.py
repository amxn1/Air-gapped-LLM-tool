import json
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from packages.contracts.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    CitationReference,
)
from ..services.llama_service import LlamaService
from services.retrieval.service import RetrievalService
from ..database import get_db
from .. import models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/chat/completions",
    tags=["chat"],
)


@router.post("", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    db: Session = Depends(get_db)
):
    """
    Create a chat completion for the provided messages.
    Fully compatible with OpenAI API format with local RAG citations and task template support.
    """
    llama_service = LlamaService()
    retrieval_service = RetrievalService(db_session=db)

    try:
        # Determine model ID
        model_profile = None
        if request.model:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.model_name == request.model,
                models.ModelProfile.status == "active"
            ).first()

        if not model_profile:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.status == "active"
            ).first()

        model_id = model_profile.id if model_profile else None
        model_name = model_profile.model_name if model_profile else (request.model or "llama-2-7b-chat")

        # Extract latest user message for retrieval
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        latest_user_message = user_messages[-1].content if user_messages else ""

        # Perform RAG retrieval if collection_id specified or if collections exist
        citations: List[CitationReference] = []
        augmented_messages = []

        if latest_user_message:
            retrieved_chunks = await retrieval_service.retrieve_relevant_chunks(
                query=latest_user_message,
                limit=5,
                collection_id=request.collection_id
            )

            if retrieved_chunks:
                for c in retrieved_chunks:
                    citations.append(CitationReference(
                        document_id=c.get("document_id") or 1,
                        filename=c.get("filename") or "Unknown Document",
                        page_or_section=c.get("page_or_section") or "Section",
                        excerpt=c.get("text", "")[:200] + "...",
                        score=c.get("score")
                    ))

                # Inject evidence context into user prompt using RAG format
                rag_prompt_data = llama_service.prompt_manager.build_rag_prompt(
                    query=latest_user_message,
                    chunks=retrieved_chunks
                )

                for msg in request.messages:
                    if msg.role == "user" and msg.content == latest_user_message:
                        augmented_messages.append({"role": "user", "content": rag_prompt_data["user_prompt"]})
                    else:
                        augmented_messages.append({"role": msg.role, "content": msg.content})
            else:
                augmented_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        else:
            augmented_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Generate completion
        result = await llama_service.generate_chat_response(
            messages=augmented_messages,
            model_id=model_id,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1024,
            stream=request.stream or False,
            task_mode=request.task_mode or "chat"
        )

        # Handle streaming response
        if request.stream:
            async def event_generator():
                created_ts = int(time.time())
                req_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                if isinstance(result, AsyncGenerator):
                    async for chunk in result:
                        text_delta = chunk.get("content", "")
                        stop_signal = chunk.get("stop", False)
                        payload = {
                            "id": req_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": model_name,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text_delta},
                                    "finish_reason": "stop" if stop_signal else None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                else:
                    yield f"data: {json.dumps({'error': 'Streaming unavailable'})}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # Non-streaming response
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        content = result.get("content", "No response generated.")

        prompt_str = " ".join([m.get("content", "") for m in augmented_messages])
        prompt_tokens = len(prompt_str.split())
        completion_tokens = len(content.split())

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=model_name,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            citations=citations if citations else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat completion endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await llama_service.close()
        await retrieval_service.close()