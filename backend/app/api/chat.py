"""Routes: POST /api/chat (Server-Sent Events stream of tokens + citations), GET /api/conversations/{id}."""
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.db import SessionLocal, get_session
from app.models import Conversation
from app.rag.answerer import ChatEvent, answer_question
from app.rag.embeddings import embed_query
from app.rag.llm import stream_chat
from app.schemas import ChatRequest, ConversationOut

router = APIRouter(prefix="/api", tags=["chat"])


def get_session_factory() -> sessionmaker:
    """The stream outlives a normal request-scoped session (FastAPI closes those
    before streaming starts), so the answerer opens its own sessions."""
    return SessionLocal


@router.post("/chat")
def chat(request: ChatRequest, session_factory: sessionmaker = Depends(get_session_factory)):
    if request.conversation_id is not None:
        with session_factory() as session:
            if session.get(Conversation, request.conversation_id) is None:
                raise HTTPException(404, "Conversation not found.")

    events = answer_question(session_factory, request.question, request.conversation_id,
                             embed=embed_query, llm=stream_chat)
    return StreamingResponse(
        _server_sent_events(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Conversation not found.")
    return conversation


def _server_sent_events(events: Iterator[ChatEvent]) -> Iterator[str]:
    # SSE format: "event: <name>\ndata: <json>\n\n" per event.
    for event in events:
        yield f"event: {event.name}\ndata: {json.dumps(event.data)}\n\n"
