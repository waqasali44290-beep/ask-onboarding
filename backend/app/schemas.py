"""Pydantic request/response models used by the API (the API contract lives here)."""
from datetime import datetime
from typing import Annotated, Literal

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
    visibility: str  # everyone | managers
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
    feedback: int | None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    messages: list[MessageOut]


Visibility = Literal["everyone", "managers"]

Role = Literal["employee", "manager", "admin"]

TicketStatus = Literal["open", "in_progress", "resolved"]


class TicketCreate(BaseModel):
    question: Question  # the user comes from the login, not the request
    # Optional: defaults to the start of the question, so "Yes, open a ticket" is one click.
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None = None
    conversation_id: int | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    question: str
    user_id: int | None
    user_name: str
    conversation_id: int | None
    status: TicketStatus
    response: str | None
    document_id: int | None  # set once the reply is in the knowledge base
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    response: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] | None = None


class ConversationSummary(BaseModel):
    id: int
    title: str  # the first question, shortened
    updated_at: datetime
    message_count: int


class TicketDraftRequest(BaseModel):
    question: Question


class TicketDraft(BaseModel):
    title: str


class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str


class DocumentUpdate(BaseModel):
    visibility: Visibility


class FeedbackRequest(BaseModel):
    rating: Literal[-1, 0, 1]  # 0 removes the rating


class AnswerLog(BaseModel):
    message_id: int
    question: str
    answer: str
    user_name: str
    created_at: datetime
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float
    no_answer: bool
    feedback: int | None


class AdminStats(BaseModel):
    answers: int
    no_answers: int
    no_answer_rate: float
    avg_latency_ms: int | None
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    thumbs_up: int
    thumbs_down: int
    tickets: dict[str, int]  # status -> count
    recent: list[AnswerLog]


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]


class UserAdminOut(UserOut):
    manager_id: int | None
    manager_name: str | None = None
    team_size: int = 0
    is_active: bool


class UserCreate(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")]
    display_name: Name
    role: Role
    password: Password
    manager_id: int | None = None


class UserUpdate(BaseModel):
    """Every field is optional: only the ones sent are changed (manager_id: null removes the manager)."""
    display_name: Name | None = None
    role: Role | None = None
    manager_id: int | None = None
    password: Password | None = None
    is_active: bool | None = None
