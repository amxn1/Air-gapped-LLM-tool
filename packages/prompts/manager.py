"""
Prompt template manager for versioned task templates and system policies.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptManager:
    """
    Manages loading, versioning, and formatting of task prompts.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Preload all JSON prompt templates from disk."""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory {self.templates_dir} does not exist.")
            return

        for file_path in self.templates_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    template_data = json.load(f)
                    name = template_data.get("name", file_path.stem)
                    self._cache[name] = template_data
            except Exception as e:
                logger.error(f"Error loading template {file_path}: {e}")

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a raw template dictionary by name."""
        if name not in self._cache:
            file_path = self.templates_dir / f"{name}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._cache[name] = json.load(f)
        return self._cache.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata."""
        return [
            {
                "name": data.get("name", k),
                "version": data.get("version", "1.0.0"),
                "description": data.get("description", "")
            }
            for k, data in self._cache.items()
        ]

    def build_chat_prompt(self, messages: List[Dict[str, str]], system_override: Optional[str] = None) -> str:
        """Construct full prompt string from chat message history."""
        template = self.get_template("general_chat")
        system_prompt = system_override or (template.get("system_prompt") if template else "You are a helpful offline assistant.")

        formatted_parts = [f"system: {system_prompt}"]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_parts.append(f"{role}: {content}")
        
        formatted_parts.append("assistant: ")
        return "\n\n".join(formatted_parts)

    def build_rag_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Construct system and user messages for evidence-grounded RAG."""
        template = self.get_template("rag_citation")
        system_prompt = template.get("system_prompt", "Answer only using provided evidence.") if template else "Answer using evidence."

        context_blocks = []
        for i, c in enumerate(chunks):
            doc_name = c.get("filename", f"Document_{c.get('document_id', i+1)}")
            section = c.get("page_or_section") or f"Chunk {c.get('chunk_index', i+1)}"
            text = c.get("text", "")
            context_blocks.append(
                f"--- Evidence Item [{i+1}] ---\nSource: {doc_name}\nSection/Page: {section}\nContent: {text}"
            )

        context_str = "\n\n".join(context_blocks)
        user_template = template.get("user_template", "{retrieved_context}\n\nUser Question:\n{user_question}") if template else "{retrieved_context}\n\nQuestion: {user_question}"
        user_prompt = user_template.format(
            retrieved_context=context_str,
            user_question=query
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "parameters": template.get("parameters", {}) if template else {}
        }

    def build_summary_prompt(self, content: str, summary_type: str = "structured") -> Dict[str, Any]:
        """Construct prompt for specific summarization types."""
        template_key = {
            "quick": "quick_summary",
            "structured": "structured_brief",
            "science-technology": "science_technology",
            "news-editorial": "news_editorial",
            "long-document": "long_document_map_reduce",
        }.get(summary_type, "structured_brief")

        template = self.get_template(template_key)
        if not template:
            template = self.get_template("structured_brief")

        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_template", "{input_text}")
        user_prompt = user_template.format(input_text=content)

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "parameters": template.get("parameters", {}),
            "template_name": template_key
        }

    def build_rewriting_prompt(self, text: str, mode: str = "formal") -> Dict[str, Any]:
        """Construct prompt for context-aware rewriting and grammar correction."""
        template = self.get_template("rewriting_grammar")
        system_prompt = template.get("system_prompt", "Rewrite the text accurately.") if template else "Rewrite accurately."
        modes = template.get("modes", {}) if template else {}
        mode_instruction = modes.get(mode, modes.get("formal", "Elevate text into clear, professional style."))

        user_template = template.get("user_template", "Mode: {mode_instruction}\n\n{input_text}") if template else "Mode: {mode_instruction}\n\n{input_text}"
        user_prompt = user_template.format(
            mode_instruction=mode_instruction,
            input_text=text
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "parameters": template.get("parameters", {}),
            "mode": mode
        }


# Singleton instance for quick imports
default_prompt_manager = PromptManager()
