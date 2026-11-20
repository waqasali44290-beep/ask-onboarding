"""Routes: POST /api/tickets/draft (suggested title), POST /api/tickets (create), GET /api/tickets."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Conversation, Ticket
from app.rag.llm import LLMError, stream_chat
from app.rag.prompts import TICKET_DRAFT_PROMPT
from app.schemas import TicketCreate, TicketDraft, TicketDraftRequest, TicketOut
from app.text import shorten

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

TITLE_LENGTH = 80


@router.post("/draft", response_model=TicketDraft)
def draft_ticket(request: TicketDraftRequest):
    """Suggest a ticket title so the user only has to confirm or edit it.
    If the LLM is unavailable, the question itself is the suggestion."""
    try:
        reply = "".join(stream_chat(TICKET_DRAFT_PROMPT, request.question)).strip()
    except LLMError:
        reply = ""
    # Small models sometimes add quotes or a second line; keep only the first line.
    title = reply.splitlines()[0].strip(' "\'') if reply else ""
    return TicketDraft(title=shorten(title or request.question, TITLE_LENGTH))


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(request: TicketCreate, session: Session = Depends(get_session)):
    """Called when the user accepts the assistant's offer after a 'not in the documents' answer."""
    if request.conversation_id is not None and session.get(Conversation, request.conversation_id) is None:
        raise HTTPException(404, "Conversation not found.")

    ticket = Ticket(
        title=request.title or shorten(request.question, TITLE_LENGTH),
        question=request.question,
        user_name=request.user_name,
        conversation_id=request.conversation_id,
    )
    session.add(ticket)
    session.commit()
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(session: Session = Depends(get_session)):
    return session.scalars(select(Ticket).order_by(Ticket.id.desc())).all()
