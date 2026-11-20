"""Suggested questions per document, written once by the LLM after ingestion.

They are shown under answers ("Related questions") and on the welcome screen.
Generating them at ingestion time means answers don't wait for an extra LLM call.
"""
import logging
import re

from sqlalchemy.orm import sessionmaker

from app.db import SessionLocal
from app.models import Document
from app.rag.llm import LLMError, StreamChat, stream_chat
from app.rag.prompts import SUGGEST_QUESTIONS_PROMPT

logger = logging.getLogger(__name__)

SUGGESTION_COUNT = 3
DOCUMENT_PREVIEW_CHARS = 2000  # enough for the model to see what the document is about


def parse_questions(reply: str) -> list[str]:
    """Keep real questions only: strip numbering/bullets, drop lines without "?"."""
    questions: list[str] = []
    for line in reply.splitlines():
        line = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip().strip('"')
        if line.endswith("?") and 8 <= len(line) <= 150 and line not in questions:
            questions.append(line)
    return questions[:SUGGESTION_COUNT]


def suggest_questions(document_id: int, session_factory: sessionmaker = SessionLocal, llm: StreamChat = stream_chat):
    """Best effort: if the LLM is down, the document just has no suggestions."""
    with session_factory() as session:
        document = session.get(Document, document_id)
        if document is None or document.status != "ready" or not document.full_text:
            return
        try:
            reply = "".join(llm(SUGGEST_QUESTIONS_PROMPT, document.full_text[:DOCUMENT_PREVIEW_CHARS]))
        except LLMError:
            logger.warning("Could not suggest questions for %s", document.filename)
            return
        document.suggested_questions = parse_questions(reply)
        session.commit()
