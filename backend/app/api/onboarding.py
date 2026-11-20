"""Routes for the onboarding journey: checklist progress and a quiz written from the documents."""
import random

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import current_user, visible_to
from app.db import get_session
from app.models import Document, OnboardingProgress, User
from app.onboarding import QUIZ_PASS_PERCENT, QUIZ_TASK, tasks_for
from app.schemas import JourneyOut, QuizItem, QuizResult, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("", response_model=JourneyOut)
def journey(user: User = Depends(current_user), session: Session = Depends(get_session)):
    progress = {row.task_id: row for row in session.scalars(select(OnboardingProgress).where(OnboardingProgress.user_id == user.id))}
    quiz = progress.get(QUIZ_TASK)
    return JourneyOut(
        tasks=[TaskOut(id=t.id, title=t.title, description=t.description, ask=t.ask, done=t.id in progress)
               for t in tasks_for(user.role)],
        quiz_best=quiz.score if quiz else None,
        quiz_pass_percent=QUIZ_PASS_PERCENT,
    )


@router.put("/tasks/{task_id}", status_code=204)
def mark_task(task_id: str, request: TaskUpdate, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if task_id not in {task.id for task in tasks_for(user.role)}:
        raise HTTPException(404, "Task not found.")
    done = session.get(OnboardingProgress, (user.id, task_id))
    if request.done and done is None:
        session.add(OnboardingProgress(user_id=user.id, task_id=task_id))
    elif not request.done:
        session.execute(delete(OnboardingProgress).where(OnboardingProgress.user_id == user.id,
                                                         OnboardingProgress.task_id == task_id))
    session.commit()


@router.get("/quiz", response_model=list[QuizItem])
def quiz(
    count: int = Query(5, ge=1, le=20),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Random quiz questions from documents this user may read. Answers are included:
    it is a self-check for learning, not an exam."""
    rows = session.execute(
        select(Document.filename, Document.quiz).where(Document.status == "ready", Document.visibility.in_(visible_to(user)))
    ).all()
    items = [QuizItem(**item, filename=filename) for filename, document_quiz in rows for item in document_quiz]
    return random.sample(items, min(count, len(items)))


@router.post("/quiz", response_model=JourneyOut)
def save_quiz_result(request: QuizResult, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if request.correct > request.total:
        raise HTTPException(422, "More correct answers than questions.")
    percent = round(100 * request.correct / request.total)
    best = session.get(OnboardingProgress, (user.id, QUIZ_TASK))
    if best is None:
        session.add(OnboardingProgress(user_id=user.id, task_id=QUIZ_TASK, score=percent))
    elif percent > (best.score or 0):
        best.score = percent  # keep the best attempt
    session.commit()
    return journey(user, session)
