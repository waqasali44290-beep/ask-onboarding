"""Route: GET /api/admin/stats -- usage, quality and cost numbers for the admin page."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.auth import require_role
from app.config import settings
from app.db import get_session
from app.models import Conversation, Message, Ticket, User
from app.schemas import AdminStats, AnswerLog
from app.text import shorten

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])

RECENT_LIMIT = 50


def cost_usd(prompt_tokens: int | None, completion_tokens: int | None) -> float:
    return round(
        ((prompt_tokens or 0) * settings.llm_cost_per_million_input_tokens
         + (completion_tokens or 0) * settings.llm_cost_per_million_output_tokens) / 1_000_000,
        6,
    )


@router.get("/stats", response_model=AdminStats)
def stats(session: Session = Depends(get_session)):
    is_answer = Message.role == "assistant"
    answers, no_answers, avg_latency, prompt_tokens, completion_tokens, up, down = session.execute(
        select(
            func.count(),
            func.count().filter(Message.no_answer),
            func.avg(Message.latency_ms),
            func.coalesce(func.sum(Message.prompt_tokens), 0),
            func.coalesce(func.sum(Message.completion_tokens), 0),
            func.count().filter(Message.feedback == 1),
            func.count().filter(Message.feedback == -1),
        ).where(is_answer)
    ).one()
    tickets = {status: count for status, count in session.execute(select(Ticket.status, func.count()).group_by(Ticket.status))}

    # The question an answer replies to = the latest user message before it in the same conversation.
    Question = aliased(Message)
    question = (
        select(Question.content)
        .where(Question.conversation_id == Message.conversation_id, Question.role == "user", Question.id < Message.id)
        .order_by(Question.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = session.execute(
        select(Message, question, User.display_name)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .outerjoin(User, User.id == Conversation.user_id)
        .where(is_answer)
        .order_by(Message.id.desc())
        .limit(RECENT_LIMIT)
    )
    recent = [
        AnswerLog(
            message_id=message.id,
            question=question_text or "",
            answer=shorten(message.content, 200),
            user_name=user_name or "unknown",
            created_at=message.created_at,
            latency_ms=message.latency_ms,
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            cost_usd=cost_usd(message.prompt_tokens, message.completion_tokens),
            no_answer=message.no_answer,
            feedback=message.feedback,
        )
        for message, question_text, user_name in rows
    ]
    return AdminStats(
        answers=answers,
        no_answers=no_answers,
        no_answer_rate=round(no_answers / answers, 3) if answers else 0.0,
        avg_latency_ms=round(avg_latency) if avg_latency is not None else None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_cost_usd=cost_usd(prompt_tokens, completion_tokens),
        thumbs_up=up,
        thumbs_down=down,
        tickets=tickets,
        recent=recent,
    )
