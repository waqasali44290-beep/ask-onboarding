"""Route: POST /api/messages/{id}/feedback (thumbs up / down on an answer)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_session
from app.models import Conversation, Message, User
from app.schemas import FeedbackRequest

router = APIRouter(prefix="/api/messages", tags=["feedback"])


@router.post("/{message_id}/feedback", status_code=204)
def rate_answer(
    message_id: int,
    request: FeedbackRequest,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Users rate answers in their own conversations; admins see the ratings on the admin page."""
    message = session.get(Message, message_id)
    if message is None or message.role != "assistant" or session.get(Conversation, message.conversation_id).user_id != user.id:
        raise HTTPException(404, "Answer not found.")
    message.feedback = request.rating or None  # 0 -> NULL (not rated)
    session.commit()
