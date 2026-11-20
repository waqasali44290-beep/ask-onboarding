"""Routes: POST /api/chat (Server-Sent Events stream of tokens + citations), GET /api/conversations/{id}."""
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import current_user, visible_to
from app.db import SessionLocal, get_session
from app.models import Conversation, Message, User
from app.rag.answerer import ChatEvent, answer_question
from app.rag.embeddings import embed_query
from app.rag.llm import stream_chat
from app.schemas import ChatRequest, ConversationOut, ConversationSummary
from app.text import shorten

router = APIRouter(prefix="/api", tags=["chat"])


def get_session_factory() -> sessionmaker:
    """The stream outlives a normal request-scoped session (FastAPI closes those
    before streaming starts), so the answerer opens its own sessions."""
    return SessionLocal


@router.post("/chat")
def chat(
    request: ChatRequest,
    user: User = Depends(current_user),
    session_factory: sessionmaker = Depends(get_session_factory),
):
    if request.conversation_id is not None:
        with session_factory() as session:
            _own_conversation_or_404(session, request.conversation_id, user)

    events = answer_question(session_factory, request.question, request.conversation_id, user.id, visible_to(user),
                             embed=embed_query, llm=stream_chat)
    return StreamingResponse(
        _server_sent_events(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Most recent first, titled by their first question (for the sidebar)."""
    stats = (
        select(
            Message.conversation_id,
            func.min(Message.id).label("first_message_id"),
            func.max(Message.created_at).label("updated_at"),
            func.count().label("message_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )
    rows = session.execute(
        select(stats.c.conversation_id, Message.content, stats.c.updated_at, stats.c.message_count)
        .join(Message, Message.id == stats.c.first_message_id)
        .join(Conversation, Conversation.id == stats.c.conversation_id)
        .where(Conversation.user_id == user.id)
        .order_by(stats.c.updated_at.desc())
        .limit(50)
    )
    return [
        ConversationSummary(id=id, title=shorten(first_question, 60), updated_at=updated_at, message_count=count)
        for id, first_question, updated_at, count in rows
    ]


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    session.delete(_own_conversation_or_404(session, conversation_id, user))  # messages go with it; tickets keep their copy of the question
    session.commit()


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    return _own_conversation_or_404(session, conversation_id, user)


def _own_conversation_or_404(session: Session, conversation_id: int, user: User) -> Conversation:
    """Someone else's conversation looks exactly like a missing one (404, not 403),
    so ids can't be used to discover other people's chats."""
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found.")
    return conversation


def _server_sent_events(events: Iterator[ChatEvent]) -> Iterator[str]:
    # SSE format: "event: <name>\ndata: <json>\n\n" per event.
    for event in events:
        yield f"event: {event.name}\ndata: {json.dumps(event.data)}\n\n"
