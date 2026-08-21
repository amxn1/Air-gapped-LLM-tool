"""
Intelligent Dynamic Model Router for Offline LLM Assistant.
Automatically classifies prompt complexity, intent, and domain to route to the optimal specialized offline model.
"""
import re
from typing import List, Optional, Tuple, Dict

# Model tier preferences per capability domain
SPECIALIST_MODEL_PREFERENCES: Dict[str, List[str]] = {
    "math_reasoning": [
        "deepseek-r1:1.5b",
        "deepseek-r1:7b",
        "deepseek-r1:8b",
        "llama3.3:70b",
        "llama3.1:8b",
        "llama3.2:3b",
        "llama3:latest",
    ],
    "coding": [
        "qwen2.5-coder:1.5b",
        "qwen2.5-coder:7b",
        "deepseek-coder:6.7b",
        "deepseek-coder:1.3b",
        "codellama:7b",
        "qwen2.5:7b",
        "llama3.2:3b",
        "llama3:latest",
    ],
    "pdf_document_reading": [
        "phi3.5:latest",
        "phi3.5:3.8b",
        "phi3:mini",
        "gemma2:2b",
        "llama3.2:3b",
        "llama3:latest",
        "gemma4:26b",
    ],
    "general_chat": [
        "llama3.2:3b",
        "llama3.2:1b",
        "llama3:latest",
        "gemma4:26b",
        "tinyllama:1.1b",
        "phi3.5:latest",
    ],
}

# Regex and keyword patterns for domain classification
MATH_PATTERNS = [
    r"\b(?:calculate|equation|integral|derivative|calculus|arithmetic|algebra|algebraic|matrix|matrices|probability|combinatorics|prime number|factorial|logarithm|trigonometry|geometry|theorem|proof|prove that|evaluate the sum|sum of|solve for [a-zA-Z]|riddle|logic puzzle|step-by-step reasoning|think step by step|chain of thought)\b",
    r"\d+\s*[\+\-\*\/\^%]\s*\d+",  # e.g. 17 * 23, 100 / 4
    r"[a-zA-Z]\s*=\s*[\d\w\+\-\*\/\^]+",  # e.g. x = 2y + 3
    r"(?:sqrt|sin|cos|tan|log|ln|lim|sum|int)\([^\)]+\)",
]

CODE_PATTERNS = [
    r"\b(?:python|javascript|typescript|c\+\+|golang|rust|java|html|css|sql|bash|powershell|regex|json|yaml|api|endpoint|docker|dockerfile|git|npm|pip|fastapi|react|vue|node\.js|uvicorn|pandas|numpy|pytorch|tensorflow)\b",
    r"\b(?:def |function |class |import |from |const |let |var |return |public class|static void|SELECT |FROM |INSERT |UPDATE |DELETE |JOIN |CREATE TABLE|try:|except |catch |async def|async function|console\.log|print\(|<div|<script|<template)\b",
    r"\b(?:write a (?:function|script|program|class|component|hook|endpoint|query|regex)|fix (?:this|the) (?:bug|error|issue|code)|debug|refactor|unit test|syntax error|type error|stack trace)\b",
    r"```[a-zA-Z0-9_-]*\n",
]

DOC_PATTERNS = [
    r"---\s*\[Attached Document:",
    r"=== DOCUMENT:",
    r"\b(?:in this (?:document|pdf|file|paper|report|policy|manual|contract|spreadsheet)|summarize (?:this|the) (?:document|pdf|file|attachment)|according to the (?:document|policy|text)|cite (?:from|the) document|key points of the attached|table of contents)\b",
]


def classify_prompt(prompt: str, has_doc_attachment: bool = False) -> Tuple[str, str]:
    """
    Classify the prompt domain and complexity.
    
    Returns:
        (category, explanation_reason)
    """
    cleaned = prompt.strip()
    
    # 1. Document / PDF Reading & Extraction
    if has_doc_attachment:
        return "pdf_document_reading", "Attached document/PDF detected; routed to document reading specialist."
    
    for pattern in DOC_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return "pdf_document_reading", "Document analysis / citation request detected; routed to PDF & long-document specialist."
    
    # 2. Code Generation & Software Engineering
    for pattern in CODE_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return "coding", "Code generation / technical programming syntax detected; routed to coding specialist."
    
    # 3. Maths, Logic, and Complex Step-by-Step Thinking
    for pattern in MATH_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return "math_reasoning", "Mathematical calculation / deep step-by-step reasoning detected; routed to logic & reasoning specialist."
    
    # 4. Fallback: General Chat & Conversational Assistant
    return "general_chat", "General conversational query; routed to fast general assistant."


def select_optimal_model(
    prompt: str,
    available_models: List[str],
    has_doc_attachment: bool = False,
    requested_model: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Determine the optimal model name, domain category, and reason.
    If requested_model is a specific model (e.g. 'deepseek-r1:1.5b'), respects user preference unless 'auto' or empty.
    
    Returns:
        (selected_model_name, domain_category, routing_reason)
    """
    # If a specific concrete model was explicitly selected (and is not 'auto' or 'auto:smart')
    if requested_model and requested_model.lower() not in ["auto", "auto:smart", "default", ""]:
        # Verify if it's available
        if requested_model in available_models or any(m.startswith(requested_model) for m in available_models):
            return requested_model, "user_selected", f"User manually selected {requested_model}."

    category, reason = classify_prompt(prompt, has_doc_attachment=has_doc_attachment)
    preferred_models = SPECIALIST_MODEL_PREFERENCES.get(category, [])
    
    # Find best matching installed model from preferred tier
    for pref in preferred_models:
        for avail in available_models:
            if pref == avail or avail.startswith(pref) or pref.startswith(avail.split(":")[0]):
                return avail, category, reason

    # Fallback to first available installed model
    fallback = available_models[0] if available_models else "llama3.2:3b"
    return fallback, category, reason
