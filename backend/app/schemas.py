"""Pydantic request/response models used by the API (the API contract lives here)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
