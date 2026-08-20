"""
Shared data contracts and Pydantic schemas for the Offline LLM Assistant.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# --- Auth & User Contracts ---
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Model Registry Contracts ---
class ModelProfileBase(BaseModel):
    model_name: str
    version: str
    format: str = "GGUF"  # GGUF, Safetensors
    quantization: Optional[str] = "q4_0"
    context_length: int = 4096
    max_output: int = 1024
    hardware_profile: Optional[str] = "CPU/GPU"
    checksum: Optional[str] = None
    approval_id: Optional[str] = None
    status: str = "staged"  # staged, smoke_testing, active, deprecated


class ModelProfileCreate(ModelProfileBase):
    pass


class ModelProfileResponse(ModelProfileBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ModelActivationRequest(BaseModel):
    hardware_profile: Optional[str] = None


# --- Chat & Completion Contracts ---
class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class CitationReference(BaseModel):
    document_id: int
    filename: str
    page_or_section: Optional[str] = None
    excerpt: str
    score: Optional[float] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    collection_id: Optional[int] = None
    task_mode: Optional[str] = "chat"
    tone_or_dialect: Optional[str] = None


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Dict[str, int]
    citations: Optional[List[CitationReference]] = None


# --- Summaries Contracts ---
class SummaryRequest(BaseModel):
    content: str
    summary_type: str = "structured"
    model: Optional[str] = None
    temperature: Optional[float] = 0.3
    max_length: Optional[int] = None


class SummaryResponse(BaseModel):
    id: str
    summary: str
    model_used: str
    created_at: str
    summary_type: str
    metadata: Optional[Dict[str, Any]] = None


# --- Rewriting Contracts ---
class RewritingRequest(BaseModel):
    text: str
    mode: str = "formal"
    model: Optional[str] = None
    temperature: Optional[float] = 0.2


class RewritingResponse(BaseModel):
    id: str
    original_text: str
    rewritten_text: str
    changes_summary: Optional[str] = None
    mode: str
    model_used: str
    created_at: str


# --- Document & Collection Contracts ---
class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    classification: str = "internal"
    access_policy: str = "authenticated"


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[str] = None
    access_policy: Optional[str] = None
    is_active: Optional[bool] = None


class CollectionResponse(CollectionBase):
    id: int
    is_active: bool
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    media_type: str
    file_size: Optional[int] = None
    collection_id: Optional[int] = None
    import_status: str
    processing_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    text: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Audit & System Contracts ---
class AuditEventResponse(BaseModel):
    id: int
    actor_id: Optional[int] = None
    action: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    result: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SystemStatsResponse(BaseModel):
    users: Dict[str, int]
    documents: Dict[str, int]
    collections: Dict[str, int]
    conversations: Dict[str, int]
    timestamp: str
