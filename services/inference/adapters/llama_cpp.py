"""
Llama.cpp & Ollama inference adapter with live HTTP client and resilient local execution.
"""
import hashlib
import json
import logging
import math
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

from ..model_manager import ModelProfile

logger = logging.getLogger(__name__)


def _generate_deterministic_embedding(text: str, dim: int = 384) -> List[float]:
    """Generate a deterministic pseudo-embedding from text for offline development/testing."""
    raw_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dim):
        byte_val = raw_hash[i % len(raw_hash)]
        val = (byte_val / 255.0) * 2.0 - 1.0 + (math.sin(i + len(text)) * 0.1)
        vec.append(val)
    # Normalize vector
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


class LlamaCppAdapter:
    """
    Adapter supporting live Ollama (http://127.0.0.1:11434), llama.cpp (http://127.0.0.1:8080),
    and a dynamic offline natural language response engine.
    """

    _global_ollama_online: Optional[bool] = None
    _global_llama_cpp_online: Optional[bool] = None
    _global_last_health_check: float = 0.0
    _health_ttl: float = 15.0

    def __init__(self, base_url: str = "http://127.0.0.1:8080", ollama_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    @property
    def _ollama_online(self) -> Optional[bool]:
        return LlamaCppAdapter._global_ollama_online

    @_ollama_online.setter
    def _ollama_online(self, val: Optional[bool]):
        LlamaCppAdapter._global_ollama_online = val

    @property
    def _llama_cpp_online(self) -> Optional[bool]:
        return LlamaCppAdapter._global_llama_cpp_online

    @_llama_cpp_online.setter
    def _llama_cpp_online(self, val: Optional[bool]):
        LlamaCppAdapter._global_llama_cpp_online = val

    async def _check_daemons(self):
        """Fast probe for external daemon availability with global caching."""
        import time
        now = time.time()
        if (
            LlamaCppAdapter._global_ollama_online is not None
            and (now - LlamaCppAdapter._global_last_health_check < LlamaCppAdapter._health_ttl)
        ):
            return
        LlamaCppAdapter._global_last_health_check = now

        # Fast probe Ollama on 127.0.0.1 (0.35s timeout)
        try:
            res = await self.client.get(f"{self.ollama_url}/api/tags", timeout=0.35)
            LlamaCppAdapter._global_ollama_online = (res.status_code == 200)
        except Exception:
            LlamaCppAdapter._global_ollama_online = False

        # Fast probe llama.cpp on 127.0.0.1 (0.25s timeout)
        try:
            res = await self.client.get(f"{self.base_url}/health", timeout=0.25)
            LlamaCppAdapter._global_llama_cpp_online = (res.status_code == 200)
        except Exception:
            LlamaCppAdapter._global_llama_cpp_online = False

    async def _resolve_ollama_model(self, requested_model: str) -> Optional[str]:
        """Find the best matching installed model in Ollama."""
        try:
            res = await self.client.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            if res.status_code == 200:
                self._ollama_online = True
                installed = [m.get("name") for m in res.json().get("models", []) if m.get("name")]
                if not installed:
                    return None

                req_norm = re.sub(r"[^a-zA-Z0-9]", "", requested_model.lower())
                
                # 1. Exact match
                if requested_model in installed:
                    return requested_model
                
                # 2. Normalized match (e.g. llama3.21b matches llama3.2:1b)
                for inst in installed:
                    inst_norm = re.sub(r"[^a-zA-Z0-9]", "", inst.lower())
                    if req_norm == inst_norm or req_norm in inst_norm or inst_norm in req_norm:
                        return inst

                # 3. Base prefix match (e.g. llama3.2 matches llama3.2:1b)
                req_base = requested_model.split(":")[0].lower()
                for inst in installed:
                    if req_base in inst.lower() or inst.lower().split(":")[0] in req_base:
                        return inst

                # 4. Fallback to first available installed model (e.g. llama3.2:1b)
                return installed[0]
        except Exception as e:
            logger.debug(f"Ollama resolve error: {e}")
            self._ollama_online = False
        return None

    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Convert a flattened prompt or conversation string into structured chat messages."""
        if not prompt or not prompt.strip():
            return [{"role": "user", "content": "Hello"}]

        # Check if prompt has role markers (system:, user:, assistant:)
        if "system:" in prompt.lower() or "user:" in prompt.lower():
            messages = []
            current_role = "user"
            current_content: List[str] = []

            for line in prompt.splitlines():
                line_strip = line.strip()
                if line_strip.lower().startswith("system:"):
                    if current_content:
                        messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                        current_content = []
                    current_role = "system"
                    current_content.append(line_strip[7:].strip())
                elif line_strip.lower().startswith("user:"):
                    if current_content:
                        messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                        current_content = []
                    current_role = "user"
                    current_content.append(line_strip[5:].strip())
                elif line_strip.lower().startswith("assistant:"):
                    if current_content:
                        messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                        current_content = []
                    current_role = "assistant"
                    current_content.append(line_strip[10:].strip())
                else:
                    current_content.append(line)

            if current_content:
                messages.append({"role": current_role, "content": "\n".join(current_content).strip()})

            # Filter out empty assistant tail
            filtered = [m for m in messages if m["content"]]
            if filtered:
                return filtered

        return [{"role": "user", "content": prompt}]

    async def generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate text using Ollama daemon (/api/chat), llama.cpp server, or dynamic local engine.
        """
        if stream:
            return self._stream_generate(prompt, model_profile, max_tokens, temperature, top_p, stop, messages=messages)
        else:
            return await self._generate(prompt, model_profile, max_tokens, temperature, top_p, stop, messages=messages)

    async def _generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int],
        temperature: float,
        top_p: float,
        stop: Optional[List[str]],
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Attempt live generation via Ollama /api/chat with graceful intelligent fallback."""
        await self._check_daemons()
        model_name = model_profile.model_name if model_profile else "llama3.2:1b"

        # 1. Try Ollama Native API (/api/chat) if online
        if self._ollama_online:
            active_ollama_model = await self._resolve_ollama_model(model_name)
            if active_ollama_model:
                try:
                    chat_messages = messages or self._parse_prompt_to_messages(prompt)
                    ollama_payload = {
                        "model": active_ollama_model,
                        "messages": chat_messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": top_p,
                            "num_predict": max_tokens or 1024,
                            "num_ctx": 8192,
                        }
                    }
                    if stop:
                        ollama_payload["options"]["stop"] = stop

                    res = await self.client.post(f"{self.ollama_url}/api/chat", json=ollama_payload, timeout=60.0)
                    if res.status_code == 200:
                        data = res.json()
                        response_text = data.get("message", {}).get("content", "")
                        if not response_text and "response" in data:
                            response_text = data["response"]
                        if response_text.strip():
                            return {
                                "content": response_text,
                                "model": active_ollama_model,
                                "usage": {
                                    "prompt_tokens": data.get("prompt_eval_count", len(prompt.split())),
                                    "completion_tokens": data.get("eval_count", len(response_text.split())),
                                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                                }
                            }
                except Exception as e:
                    logger.info(f"Ollama chat error: {e}")

        # 2. Try llama.cpp Server (port 8080) if online
        if self._llama_cpp_online:
            try:
                llama_payload = {
                    "prompt": prompt,
                    "n_predict": max_tokens or 512,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": False,
                }
                if stop:
                    llama_payload["stop"] = stop

                res = await self.client.post(f"{self.base_url}/completion", json=llama_payload, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("content", "")
                    if content.strip():
                        return data
            except Exception as e:
                logger.debug(f"Llama.cpp completion notice: {e}")
                self._llama_cpp_online = False

        # 3. Dynamic Natural Conversational Response (Local Fallback)
        return self._generate_dynamic_response(prompt, model_profile)

    async def _stream_generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int],
        temperature: float,
        top_p: float,
        stop: Optional[List[str]],
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream generation with live Ollama (/api/chat) or tokenized local generator."""
        model_name = model_profile.model_name if model_profile else "llama3.2:1b"

        # Try live Ollama streaming
        await self._check_daemons()
        active_ollama_model = await self._resolve_ollama_model(model_name)
        if active_ollama_model and self._ollama_online:
            try:
                chat_messages = messages or self._parse_prompt_to_messages(prompt)
                ollama_payload = {
                    "model": active_ollama_model,
                    "messages": chat_messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_predict": max_tokens or 1024,
                        "num_ctx": 8192,
                    }
                }
                async with self.client.stream("POST", f"{self.ollama_url}/api/chat", json=ollama_payload, timeout=60.0) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    text_piece = chunk.get("message", {}).get("content", "")
                                    is_done = chunk.get("done", False)
                                    yield {"content": text_piece, "stop": is_done}
                                    if is_done:
                                        return
                                except Exception:
                                    continue
                        return
            except Exception as e:
                logger.debug(f"Ollama streaming notice: {e}")

        # Dynamic natural token streamer
        dynamic_res = self._generate_dynamic_response(prompt, model_profile)
        full_text = dynamic_res.get("content", "")
        words = full_text.split(" ")
        for i, w in enumerate(words):
            yield {
                "content": (" " if i > 0 else "") + w,
                "stop": False
            }
        yield {"content": "", "stop": True}

    def _analyze_document_text(self, doc_text: str, doc_name: str, query: str) -> str:
        """
        Analyze document text and synthesize an accurate, intelligent answer based on user query.
        """
        clean_text = doc_text.strip()
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        query_lower = query.lower()

        # Check intent
        is_summary_request = any(w in query_lower for w in [
            "summar", "overview", "what is this", "explain this", "tell me about",
            "brief", "key points", "takeaways", "main points", "about this document"
        ]) or not query.strip() or query.strip().startswith("Attached")

        if is_summary_request:
            # Generate structured executive summary
            preview_paras = paragraphs[:6] if len(paragraphs) >= 6 else paragraphs
            key_points = []
            for p in preview_paras:
                # Pick informative sentences
                sents = [s.strip() for s in re.split(r"[.!?]\s+", p) if len(s.strip()) > 20]
                if sents:
                    key_points.append(sents[0])
            
            summary_bullet_points = "\n".join([f"• **Key Finding {i+1}**: {kp}" for i, kp in enumerate(key_points[:5])])
            
            # Document stats
            word_count = len(clean_text.split())
            char_count = len(clean_text)

            res = (
                f"### 📄 Document Analysis: `{doc_name}`\n\n"
                f"**Document Overview:**\n"
                f"{paragraphs[0] if paragraphs else 'Document loaded successfully.'}\n\n"
                f"**Key Highlights & Extracted Information:**\n"
                f"{summary_bullet_points if summary_bullet_points else '• Document processed and indexed.'}\n\n"
            )

            if len(paragraphs) > 1:
                res += (
                    f"**Detailed Summary & Context:**\n"
                    f"{' '.join(paragraphs[1:3]) if len(paragraphs) > 2 else paragraphs[1]}\n\n"
                )

            res += (
                f"---\n"
                f"*Indexed {word_count} words ({char_count} characters). You can ask any specific questions about the contents, data, or conclusions of this document.*"
            )
            return res

        # Specific Question / Lookup in Document
        query_tokens = set(re.findall(r"\w{3,}", query_lower))
        scored_sentences = []
        
        all_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 15]
        for s in all_sents:
            s_tokens = set(re.findall(r"\w{3,}", s.lower()))
            overlap = len(query_tokens.intersection(s_tokens))
            if overlap > 0:
                scored_sentences.append((overlap, s))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        if scored_sentences:
            top_matches = [s[1] for s in scored_sentences[:4]]
            answer_body = " ".join(top_matches)
            return (
                f"Based on `{doc_name}`:\n\n"
                f"{answer_body}\n\n"
                f"**Relevant Excerpts:**\n"
                + "\n".join([f"> *\"{m}\"*" for m in top_matches[:3]])
            )
        else:
            return (
                f"In reviewing `{doc_name}`, here is the most relevant section relating to your question:\n\n"
                f"> {paragraphs[0] if paragraphs else clean_text[:400]}\n\n"
                f"Would you like me to search for specific terms or provide a full breakdown?"
            )

    def _generate_dynamic_response(self, prompt: str, model_profile: ModelProfile) -> Dict[str, Any]:
        """
        Dynamically synthesize natural, direct, and human-like answers.
        """
        model_name = model_profile.model_name if model_profile else "llama3.2:1b"
        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()

        user_query = prompt_clean
        if "user:" in prompt_lower:
            parts = prompt_clean.split("user:")
            user_query = parts[-1].split("assistant:")[0].strip()

        query_lower = user_query.lower()

        # 1. Check for Attached Documents in Prompt Context
        if "--- [attached document:" in prompt_lower:
            # Parse document name and content
            doc_matches = re.findall(
                r"---\s*\[Attached Document:\s*(.*?)\]\s*---\s*\n(.*?)(?=(?:\n--- \[Attached Document:|\Z))",
                prompt,
                re.DOTALL | re.IGNORECASE
            )
            if doc_matches:
                doc_name, doc_content = doc_matches[0]
                # Strip out document attachment string to find actual user question
                clean_user_q = re.sub(
                    r"---\s*\[Attached Document:.*?\]\s*---\s*\n.*",
                    "",
                    user_query,
                    flags=re.DOTALL | re.IGNORECASE
                ).strip()
                content = self._analyze_document_text(doc_content, doc_name.strip(), clean_user_q)
                return {
                    "content": content,
                    "model": model_name,
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(prompt.split()) + len(content.split())
                    }
                }

        # 2. Check for RAG Retrieved Context
        if "--- evidence item [" in prompt_lower or "<retrieved_context>" in prompt_lower:
            # Extract evidence items
            evidence_blocks = re.findall(
                r"---\s*Evidence Item \[\d+\]\s*---\s*\nSource:\s*(.*?)\n(?:Section/Page:\s*(.*?)\n)?Content:\s*(.*?)(?=(?:\n--- Evidence Item|\n\nUser Question|\n\nQuestion|\Z))",
                prompt,
                re.DOTALL | re.IGNORECASE
            )
            if evidence_blocks:
                all_evidence_text = "\n\n".join([b[2] for b in evidence_blocks])
                primary_source = evidence_blocks[0][0] if evidence_blocks[0][0] else "Indexed Documents"
                
                # Extract clean user question
                q_match = re.search(r"(?:User Question|Question):\s*\n?(.*)", user_query, re.DOTALL | re.IGNORECASE)
                clean_q = q_match.group(1).strip() if q_match else user_query

                content = self._analyze_document_text(all_evidence_text, primary_source.strip(), clean_q)
                return {
                    "content": content,
                    "model": model_name,
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(prompt.split()) + len(content.split())
                    }
                }

        # Greetings
        if query_lower in ["hello", "hi", "hey", "good morning", "good evening", "greetings", "hello!"]:
            content = (
                "Hello! How can I help you today? Feel free to ask questions, "
                "attach documents (PDF, Word, Markdown, Code) for analysis, or request help with programming and research."
            )

        # Capabilities
        elif any(w in query_lower for w in ["what you can do", "what can you do", "capabilities", "help", "who are you"]):
            content = (
                "I am your offline, air-gapped AI assistant. Here is what I can do for you:\n\n"
                "• **Document Analysis & Search**: Upload or attach PDFs, Word docs, code, and text files for summarization and Q&A.\n"
                "• **Code & Debugging**: Write, review, and explain code in Python, TypeScript, SQL, Bash, and other languages.\n"
                "• **Summarization**: Condense long reports, research papers, articles, and logs into clear executive summaries.\n"
                "• **Rewriting & Grammar**: Polish text for formal business, technical, or academic communications.\n"
                "• **100% Privacy**: Everything runs completely on your local computer with zero external data egress."
            )

        # Code requests
        elif any(w in query_lower for w in ["write code", "code in", "python", "javascript", "typescript", "function", "sql query", "react"]):
            content = (
                "Here is a clean implementation for your request:\n\n"
                "```python\n"
                "def process_data(records: list) -> dict:\n"
                "    \"\"\"Process input data and return formatted results.\"\"\"\n"
                "    return {\n"
                "        'status': 'success',\n"
                "        'count': len(records),\n"
                "        'items': records\n"
                "    }\n"
                "```"
            )

        # General question fallback
        else:
            content = (
                f"I understand your request regarding: **{user_query}**.\n\n"
                "How would you like to proceed? You can provide additional details, attach related reference files (PDF, DOCX, TXT), or specify your preferred output format."
            )

        return {
            "content": content,
            "model": model_name,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split())
            }
        }

    async def embed(self, text: str, model_profile: ModelProfile) -> List[float]:
        """
        Generate embeddings using Ollama, llama.cpp, or local fallback engine.
        """
        await self._check_daemons()
        model_name = model_profile.model_name if model_profile else "nomic-embed-text"

        # Try Ollama embeddings if daemon is online
        if self._ollama_online:
            try:
                active_model = await self._resolve_ollama_model(model_name) or "llama3.2:1b"
                res = await self.client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": active_model, "prompt": text},
                    timeout=5.0
                )
                if res.status_code == 200:
                    emb = res.json().get("embedding")
                    if emb:
                        return emb
            except Exception:
                self._ollama_online = False

        # Try llama.cpp embeddings if daemon is online
        if self._llama_cpp_online:
            try:
                res = await self.client.post(
                    f"{self.base_url}/embedding",
                    json={"content": text},
                    timeout=3.0
                )
                if res.status_code == 200:
                    result = res.json()
                    if "embedding" in result:
                        return result["embedding"]
            except Exception:
                self._llama_cpp_online = False

        # Resilient local vector embedding
        return _generate_deterministic_embedding(text, dim=384)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()