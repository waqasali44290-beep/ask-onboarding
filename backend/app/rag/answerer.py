"""Orchestrates one question: retrieve -> no-answer check -> prompt LLM -> stream tokens and citations."""
import logging
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Conversation, Message
from app.rag.llm import LLMError, StreamChat
from app.rag.prompts import NO_ANSWER_MESSAGE, NOT_FOUND_MARKER, SYSTEM_PROMPT, build_user_message
from app.rag.retriever import QueryEmbedder, relevant_chunks, search

logger = logging.getLogger(__name__)

LLM_UNAVAILABLE_MESSAGE = "The assistant is unavailable right now. Please try again in a few minutes."


@dataclass
class ChatEvent:
    name: str  # sources | token | no_answer | error | done
    data: dict


def answer_question(
    session_factory: sessionmaker,
    question: str,
    conversation_id: int | None,
    embed: QueryEmbedder,
    llm: StreamChat,
) -> Iterator[ChatEvent]:
    """Yields events in this order:
    sources -> token... -> done                  (answered)
    [sources ->] no_answer -> done               (not in the documents)
    [sources ->] error                           (LLM unreachable)
    """
    with session_factory() as session:
        if conversation_id is None:
            conversation = Conversation()
            session.add(conversation)
            session.flush()  # assigns conversation.id
            conversation_id = conversation.id
        session.add(Message(conversation_id=conversation_id, role="user", content=question))
        session.commit()
        chunks = relevant_chunks(search(session, question, settings.top_k, embed=embed), settings.min_similarity)

    # Layer 1: nothing similar enough -> answer "not found" without calling the LLM.
    if not chunks:
        yield from _no_answer(session_factory, conversation_id)
        return

    sources = [{"n": number, **asdict(chunk)} for number, chunk in enumerate(chunks, start=1)]
    yield ChatEvent("sources", {"sources": sources})

    answer = ""
    streaming = False  # becomes True once we know the reply is not the NOT_FOUND marker
    try:
        for piece in llm(SYSTEM_PROMPT, build_user_message(question, chunks)):
            answer += piece
            if streaming:
                yield ChatEvent("token", {"text": piece})
                continue
            # Hold back the first characters: if they spell NOT_FOUND, the user must
            # see the no-answer message, not the raw marker.
            start = answer.lstrip()
            if NOT_FOUND_MARKER.startswith(start):
                continue  # still could be the marker, keep waiting
            if start.startswith(NOT_FOUND_MARKER):
                break
            streaming = True
            yield ChatEvent("token", {"text": start})
    except LLMError:
        logger.exception("LLM call failed")
        yield ChatEvent("error", {"message": LLM_UNAVAILABLE_MESSAGE})
        return

    # Layer 2: the model read the sources and said they don't answer the question.
    # Also catches a model that wrote some text and then the marker.
    if not answer.strip() or NOT_FOUND_MARKER in answer:
        yield from _no_answer(session_factory, conversation_id)
        return

    citations = _cited_sources(answer, sources)
    with session_factory() as session:
        message = Message(conversation_id=conversation_id, role="assistant", content=answer.strip(), citations=citations)
        session.add(message)
        session.commit()
        yield ChatEvent("done", {"conversation_id": conversation_id, "message_id": message.id,
                                 "citations": citations, "no_answer": False})


def _cited_sources(answer: str, sources: list[dict]) -> list[dict]:
    """Only the sources the answer refers to with [n]; numbers the model made up are ignored."""
    cited_numbers = {int(number) for number in re.findall(r"\[(\d+)\]", answer)}
    return [source for source in sources if source["n"] in cited_numbers]


def _no_answer(session_factory: sessionmaker, conversation_id: int) -> Iterator[ChatEvent]:
    with session_factory() as session:
        message = Message(conversation_id=conversation_id, role="assistant", content=NO_ANSWER_MESSAGE, no_answer=True)
        session.add(message)
        session.commit()
    yield ChatEvent("no_answer", {"message": NO_ANSWER_MESSAGE, "offer_ticket": True})
    yield ChatEvent("done", {"conversation_id": conversation_id, "message_id": message.id,
                             "citations": [], "no_answer": True})
