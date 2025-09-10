from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class User(BaseModel):
    user_id: str
    email: str
    name: str

class DocumentMetadata(BaseModel):
    document_id: str
    user_id: str
    filename: str
    original_name: str
    file_size: int
    s3_key: str
    processing_status: str
    chunk_count: int
    qdrant_collection: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ChunkData(BaseModel):
    chunk_id: int
    document_id: str
    text: str
    chunk_index: int
    chunk_size: int
    created_at: datetime

class EmbeddingResult(BaseModel):
    chunk_id: int
    score: float
    text: str
    document_id: str
    chunk_index: int

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    response: str
    context_chunks: List[EmbeddingResult] = []
    sources: List[str] = []

class JobProgress(BaseModel):
    percent: int = Field(..., ge=0, le=100)
    message: str

class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    progress: Optional[JobProgress] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class UploadResponse(BaseModel):
    job_id: str
    message: str
    document_id: str

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]

class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total: int

class DeleteDocumentResponse(BaseModel):
    message: str
    deleted_chunks: int

# Chat schemas
class ChatCreate(BaseModel):
    title: str
    document_id: str

class ChatInfo(BaseModel):
    chat_id: str
    user_id: str
    document_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatListResponse(BaseModel):
    chats: List[ChatInfo]
    total: int

# Chat Message schemas
class ChatMessageCreate(BaseModel):
    content: str
    sources: Optional[str] = None

class ChatMessageInfo(BaseModel):
    message_id: str
    chat_id: str
    role: str  # "user" or "assistant"
    content: str
    sources: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatWithMessages(ChatInfo):
    messages: List[ChatMessageInfo] = []

# Updated upload response
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    s3_key: str
    processing_status: str
    message: str
    process_id: str
