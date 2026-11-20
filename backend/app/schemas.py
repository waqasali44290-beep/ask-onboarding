"""Pydantic request/response models used by the API (the API contract lives here)."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Trimmed, non-empty user question. The length cap keeps one request from
# sending a whole book to the embedding model.
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    mime_type: str
    status: str  # processing | ready | failed
    error: str | None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentOut):
    full_text: str | None  # shown in the citation viewer


class RetrieveRequest(BaseModel):
    question: Question
    top_k: int | None = Field(default=None, ge=1, le=20)  # None = TOP_K from settings


class RetrievedChunkOut(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    content: str
    start_char: int
    end_char: int
    page: int | None
    score: float
    relevant: bool  # score >= MIN_SIMILARITY


class RetrieveResponse(BaseModel):
    chunks: list[RetrievedChunkOut]
    answerable: bool  # False -> no chunk is relevant -> "not in the documents"


class ChatRequest(BaseModel):
    question: Question
    conversation_id: int | None = None  # None starts a new conversation


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    citations: list[dict]
    no_answer: bool
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    messages: list[MessageOut]


class TicketCreate(BaseModel):
    question: Question
    user_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    # Optional: defaults to the start of the question, so "Yes, open a ticket" is one click.
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None
    conversation_id: int | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    question: str
    user_name: str
    conversation_id: int | None
    status: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: int
    title: str  # the first question, shortened
    updated_at: datetime
    message_count: int


class TicketDraftRequest(BaseModel):
    question: Question


class TicketDraft(BaseModel):
    title: str
