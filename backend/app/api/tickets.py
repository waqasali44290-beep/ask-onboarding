"""Routes: draft, create, list and update help-desk tickets.

Who sees what: employees see their own tickets, managers also see their
team's (read-only), admins see all. Owners can close their own ticket;
only admins reply and change the status.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_session
from app.models import Conversation, Ticket, User
from app.rag.llm import LLMError, stream_chat
from app.rag.prompts import TICKET_DRAFT_PROMPT
from app.schemas import TicketCreate, TicketDraft, TicketDraftRequest, TicketOut, TicketStatus, TicketUpdate
from app.text import shorten

router = APIRouter(prefix="/api/tickets", tags=["tickets"], dependencies=[Depends(current_user)])

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
def create_ticket(request: TicketCreate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Called when the user accepts the assistant's offer after a 'not in the documents' answer."""
    if request.conversation_id is not None:
        conversation = session.get(Conversation, request.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise HTTPException(404, "Conversation not found.")

    ticket = Ticket(
        title=request.title or shorten(request.question, TITLE_LENGTH),
        question=request.question,
        user_id=user.id,
        user_name=user.display_name,
        conversation_id=request.conversation_id,
    )
    session.add(ticket)
    session.commit()
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    status: TicketStatus | None = None,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    query = select(Ticket).order_by(Ticket.id.desc())
    if user.role == "manager":
        team = select(User.id).where(User.manager_id == user.id)
        query = query.where(or_(Ticket.user_id == user.id, Ticket.user_id.in_(team)))
    elif user.role != "admin":
        query = query.where(Ticket.user_id == user.id)
    if status:
        query = query.where(Ticket.status == status)
    return session.scalars(query).all()


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    request: TicketUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    ticket = session.get(Ticket, ticket_id)
    is_admin = user.role == "admin"
    if ticket is None or (not is_admin and ticket.user_id != user.id):
        raise HTTPException(404, "Ticket not found.")
    # Non-admins may only close their own ticket ("my question is solved").
    if not is_admin and (request.response is not None or request.status not in (None, "resolved")):
        raise HTTPException(403, "Only the help desk can change this.")

    if request.response is not None:
        ticket.response = request.response
    if request.status is not None and request.status != ticket.status:
        ticket.status = request.status
        ticket.resolved_at = datetime.now(timezone.utc) if request.status == "resolved" else None
    session.commit()
    return ticket
