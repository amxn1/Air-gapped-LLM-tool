import json
import logging
import re
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
from services.inference.model_router import select_optimal_model
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
    Fully compatible with OpenAI API format with local RAG citations, task template support,
    and automated dynamic model routing based on prompt complexity and domain.
    """
    llama_service = LlamaService()
    retrieval_service = RetrievalService(db_session=db)

    try:
        # Extract latest user message
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        latest_user_message = user_messages[-1].content if user_messages else ""

        # Check if direct document attachment is in the latest user message
        is_direct_doc = "--- [attached document:" in latest_user_message.lower()
        doc_matches = []
        if is_direct_doc:
            doc_matches = re.findall(
                r"---\s*\[Attached Document:\s*(.*?)\]\s*---\s*\n(.*?)(?=(?:\n--- \[Attached Document:|\Z))",
                latest_user_message,
                re.DOTALL | re.IGNORECASE
            )

        # Dynamic Model Routing according to prompt complexity & intent
        from .models import _sync_ollama_models
        await _sync_ollama_models(db)

        all_profiles = db.query(models.ModelProfile).all()
        available_model_names = [p.model_name for p in all_profiles if p.model_name]

        model_name, domain_cat, routing_reason = select_optimal_model(
            prompt=latest_user_message,
            available_models=available_model_names,
            has_doc_attachment=bool(doc_matches),
            requested_model=request.model
        )

        model_profile = db.query(models.ModelProfile).filter(
            models.ModelProfile.model_name == model_name
        ).first()

        if not model_profile and all_profiles:
            model_profile = db.query(models.ModelProfile).filter(
                models.ModelProfile.status == "active"
            ).first() or all_profiles[0]
            model_name = model_profile.model_name

        model_id = model_profile.id if model_profile else None

        citations: List[CitationReference] = []
        augmented_messages = []



        if doc_matches:
            # 1. Direct Document Analysis & Summarization Flow
            doc_name, doc_content = doc_matches[0]
            clean_user_q = re.sub(
                r"---\s*\[Attached Document:.*?\]\s*---\s*\n.*",
                "",
                latest_user_message,
                flags=re.DOTALL | re.IGNORECASE
            ).strip()

            if not clean_user_q or clean_user_q.startswith("Attached ") or "please analyze" in clean_user_q.lower():
                if request.task_mode == "summarize":
                    clean_user_q = "Please provide a comprehensive structured summary of this document, including document overview, key findings, and main points."
                elif request.task_mode == "science":
                    clean_user_q = "Please analyze the scientific methodology, technical principles, and key data points in this document."
                elif request.task_mode == "news":
                    clean_user_q = "Please provide an executive editorial brief and key takeaways from this document."
                elif request.task_mode == "rewriter":
                    clean_user_q = "Please review and polish the text in this document for optimal clarity and grammar."
                else:
                    clean_user_q = "Please summarize and explain the key contents of this document."

            system_instruction = (
                "You are an expert document reading and analysis assistant operating in an offline environment.\n"
                "Your task is to carefully read the provided document and answer the user's request accurately based strictly on what is written.\n"
                "- If asked to summarize, produce a structured summary: Document Overview, Key Highlights & Sections, and Important Details.\n"
                "- If the document contains placeholder text (such as Lorem Ipsum / sample text), state that clearly.\n"
                "- If asked a specific question, answer it directly using evidence from the document text.\n"
                "- Do not invent facts or extrapolate beyond what is stated in the document."
            )

            formatted_user_prompt = (
                f"=== DOCUMENT: {doc_name.strip()} ===\n"
                f"{doc_content.strip()}\n\n"
                f"=== USER REQUEST ===\n"
                f"{clean_user_q}"
            )

            augmented_messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": formatted_user_prompt}
            ]

            citations.append(CitationReference(
                document_id=1,
                filename=doc_name.strip(),
                page_or_section="Attached Document",
                excerpt=doc_content.strip()[:250] + ("..." if len(doc_content.strip()) > 250 else ""),
                score=1.0
            ))

        elif latest_user_message:
            # 2. Grounded RAG Knowledge Base Retrieval Flow
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

                evidence_text = "\n\n".join([
                    f"--- Evidence Item [{i+1}] ---\nSource: {c.get('filename')}\nSection/Page: {c.get('page_or_section')}\nContent:\n{c.get('text', '')}"
                    for i, c in enumerate(retrieved_chunks)
                ])

                system_instruction = (
                    "You are a grounded knowledge assistant operating in an offline environment.\n"
                    "Answer the user's question using ONLY the provided evidence passages in <retrieved_context>.\n"
                    "Every statement of fact should cite the relevant source document [Source: <filename>, Section: <page_or_section>].\n"
                    "If the provided context does not contain sufficient evidence, state that clearly."
                )

                formatted_user_prompt = (
                    f"<retrieved_context>\n{evidence_text}\n</retrieved_context>\n\n"
                    f"User Question:\n{latest_user_message}"
                )

                augmented_messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": formatted_user_prompt}
                ]
            else:
                augmented_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        else:
            augmented_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Generate completion with low temperature for high fidelity
        effective_temp = request.temperature if request.temperature is not None else 0.1
        result = await llama_service.generate_chat_response(
            messages=augmented_messages,
            model_id=model_id,
            temperature=effective_temp,
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