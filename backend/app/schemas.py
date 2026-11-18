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
