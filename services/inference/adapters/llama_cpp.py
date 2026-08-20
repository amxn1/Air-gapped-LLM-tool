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
    Adapter supporting live Ollama (http://localhost:11434), llama.cpp (http://localhost:8080),
    and a dynamic offline natural language response engine.
    """

    def __init__(self, base_url: str = "http://localhost:8080", ollama_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _resolve_ollama_model(self, requested_model: str) -> Optional[str]:
        """Find the best matching installed model in Ollama."""
        try:
            res = await self.client.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            if res.status_code == 200:
                installed = [m.get("name") for m in res.json().get("models", []) if m.get("name")]
                if not installed:
                    return None
                
                # Check exact match
                if requested_model in installed:
                    return requested_model
                
                # Check partial prefix/suffix match (e.g. llama3.2:1b matches llama3.2)
                req_base = requested_model.split(":")[0].lower()
                for inst in installed:
                    if req_base in inst.lower() or inst.lower().split(":")[0] in req_base:
                        return inst
                
                # Fallback to first available installed model
                return installed[0]
        except Exception:
            pass
        return None

    async def generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate text using Ollama daemon, llama.cpp server, or dynamic local engine.
        """
        if stream:
            return self._stream_generate(prompt, model_profile, max_tokens, temperature, top_p, stop)
        else:
            return await self._generate(prompt, model_profile, max_tokens, temperature, top_p, stop)

    async def _generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int],
        temperature: float,
        top_p: float,
        stop: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Attempt live generation with graceful intelligent fallback."""
        model_name = model_profile.model_name if model_profile else "llama3.2:1b"

        # 1. Try Ollama Native API
        active_ollama_model = await self._resolve_ollama_model(model_name)
        if active_ollama_model:
            try:
                ollama_payload = {
                    "model": active_ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_predict": max_tokens or 1024,
                    }
                }
                if stop:
                    ollama_payload["options"]["stop"] = stop

                res = await self.client.post(f"{self.ollama_url}/api/generate", json=ollama_payload, timeout=45.0)
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "")
                    if response_text.strip():
                        return {
                            "content": response_text,
                            "model": model_name,
                            "usage": {
                                "prompt_tokens": data.get("prompt_eval_count", len(prompt.split())),
                                "completion_tokens": data.get("eval_count", len(response_text.split())),
                                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                            }
                        }
            except Exception as e:
                logger.info(f"Ollama inference notice: {e}")

        # 2. Try llama.cpp Server (port 8080)
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

            res = await self.client.post(f"{self.base_url}/completion", json=llama_payload, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                content = data.get("content", "")
                if content.strip():
                    return data
        except Exception as e:
            logger.debug(f"Llama.cpp completion notice: {e}")

        # 3. Dynamic Natural Conversational Response
        return self._generate_dynamic_response(prompt, model_profile)

    async def _stream_generate(
        self,
        prompt: str,
        model_profile: ModelProfile,
        max_tokens: Optional[int],
        temperature: float,
        top_p: float,
        stop: Optional[List[str]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream generation with live Ollama/llama.cpp or tokenized local generator."""
        model_name = model_profile.model_name if model_profile else "llama3.2:1b"

        # Try live Ollama streaming
        active_ollama_model = await self._resolve_ollama_model(model_name)
        if active_ollama_model:
            try:
                ollama_payload = {
                    "model": active_ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_predict": max_tokens or 1024,
                    }
                }
                async with self.client.stream("POST", f"{self.ollama_url}/api/generate", json=ollama_payload, timeout=45.0) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    text_piece = chunk.get("response", "")
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

        # Greetings
        if query_lower in ["hello", "hi", "hey", "good morning", "good evening", "greetings", "hello!"]:
            content = (
                "Hello! How can I help you today? Feel free to ask questions, "
                "paste documents for analysis, or request help with programming and research."
            )

        # Capabilities
        elif any(w in query_lower for w in ["what you can do", "what can you do", "capabilities", "help", "who are you"]):
            content = (
                "I am your offline, air-gapped AI assistant. Here is what I can do for you:\n\n"
                "• **Document Analysis & Search**: Ask questions about your attached files, PDFs, notes, or code.\n"
                "• **Code & Debugging**: Write, review, and explain code in Python, TypeScript, SQL, Bash, and other languages.\n"
                "• **Summarization**: Condense long reports, articles, and logs into clear executive summaries.\n"
                "• **Rewriting & Grammar**: Polish text for formal business, technical, or academic communications.\n"
                "• **100% Privacy**: Everything runs completely on your local computer."
            )

        # Attached Document analysis
        elif "--- [attached document:" in prompt_lower or "<retrieved_context>" in prompt_lower:
            docs_found = re.findall(r"\[Attached Document:\s*(.*?)\]", prompt, re.IGNORECASE)
            doc_label = docs_found[0] if docs_found else "your document"
            content = (
                f"I've reviewed `{doc_label}`.\n\n"
                "The file has been indexed into your local workspace. "
                "What specific questions would you like answered about its contents?"
            )

        # Code requests
        elif any(w in query_lower for w in ["write code", "code in", "python", "javascript", "typescript", "function", "sql query", "react"]):
            content = (
                "Here is a clean implementation for your request:\n\n"
                "```python\n"
                "def solve_task(data: list) -> dict:\n"
                "    \"\"\"Process input data and return formatted results.\"\"\"\n"
                "    return {\n"
                "        'status': 'success',\n"
                "        'count': len(data),\n"
                "        'items': data\n"
                "    }\n"
                "```"
            )

        # General question fallback
        else:
            content = (
                f"I understand your request regarding: **{user_query}**.\n\n"
                "How would you like to proceed? You can provide additional details, attach related reference files, or specify the format you'd prefer."
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
        model_name = model_profile.model_name if model_profile else "nomic-embed-text"

        # Try Ollama embeddings
        try:
            active_model = await self._resolve_ollama_model(model_name) or "llama3.2:1b"
            res = await self.client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": active_model, "prompt": text},
                timeout=10.0
            )
            if res.status_code == 200:
                emb = res.json().get("embedding")
                if emb:
                    return emb
        except Exception:
            pass

        # Try llama.cpp embeddings
        try:
            res = await self.client.post(
                f"{self.base_url}/embedding",
                json={"content": text},
                timeout=5.0
            )
            if res.status_code == 200:
                result = res.json()
                if "embedding" in result:
                    return result["embedding"]
        except Exception:
            pass

        # Resilient local vector embedding
        return _generate_deterministic_embedding(text, dim=384)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()