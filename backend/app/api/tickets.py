"""Routes: POST /api/tickets (create help-desk ticket), GET /api/tickets."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Conversation, Ticket
from app.schemas import TicketCreate, TicketOut

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

TITLE_LENGTH = 80


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(request: TicketCreate, session: Session = Depends(get_session)):
    """Called when the user accepts the assistant's offer after a 'not in the documents' answer."""
    if request.conversation_id is not None and session.get(Conversation, request.conversation_id) is None:
        raise HTTPException(404, "Conversation not found.")

    ticket = Ticket(
        title=request.title or _title_from(request.question),
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


def _title_from(question: str) -> str:
    """First TITLE_LENGTH characters of the question, cut at a word boundary."""
    if len(question) <= TITLE_LENGTH:
        return question
    return question[:TITLE_LENGTH].rsplit(" ", 1)[0] + "…"
