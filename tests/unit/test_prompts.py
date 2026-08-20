"""
Unit tests for the PromptManager and versioned prompt templates.
"""
import pytest
from packages.prompts.manager import PromptManager


@pytest.fixture
def prompt_mgr():
    return PromptManager()


def test_list_templates(prompt_mgr):
    templates = prompt_mgr.list_templates()
    assert len(templates) >= 7
    names = [t["name"] for t in templates]
    assert "general_chat" in names
    assert "quick_summary" in names
    assert "structured_brief" in names
    assert "science_technology" in names
    assert "news_editorial" in names
    assert "rewriting_grammar" in names
    assert "rag_citation" in names


def test_build_chat_prompt(prompt_mgr):
    messages = [
        {"role": "user", "content": "What is air-gapping?"}
    ]
    prompt = prompt_mgr.build_chat_prompt(messages)
    assert "system:" in prompt
    assert "user: What is air-gapping?" in prompt
    assert "assistant:" in prompt


def test_build_rag_prompt(prompt_mgr):
    chunks = [
        {
            "filename": "security_whitepaper.pdf",
            "page_or_section": "Page 4",
            "text": "Air-gapped systems prohibit all external network interfaces."
        }
    ]
    rag_data = prompt_mgr.build_rag_prompt(query="Explain air-gap rules", chunks=chunks)
    assert "system_prompt" in rag_data
    assert "security_whitepaper.pdf" in rag_data["user_prompt"]
    assert "Explain air-gap rules" in rag_data["user_prompt"]
    assert "<retrieved_context>" in rag_data["user_prompt"]


def test_build_summary_prompt(prompt_mgr):
    science_data = prompt_mgr.build_summary_prompt(
        content="Research paper discussing novel local language model architectures.",
        summary_type="science-technology"
    )
    assert science_data["template_name"] == "science_technology"
    assert "Research paper" in science_data["user_prompt"]


def test_build_rewriting_prompt(prompt_mgr):
    rewrite_data = prompt_mgr.build_rewriting_prompt(
        text="The team are deploying the model today.",
        mode="grammar"
    )
    assert "grammar" in rewrite_data["user_prompt"].lower()
    assert "The team are deploying" in rewrite_data["user_prompt"]
