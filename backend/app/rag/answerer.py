"""Orchestrates one question: retrieve -> no-answer check -> prompt LLM -> stream tokens and citations."""
import logging
import re
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Conversation, Message
from app.rag.llm import LLMError, StreamChat
from app.rag.prompts import NO_ANSWER_MESSAGE, NOT_FOUND_MARKER, SYSTEM_PROMPT, build_user_message
from app.rag.retriever import QueryEmbedder, RetrievedChunk, relevant_chunks, search

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
    user_id: int | None,
    visibilities: list[str],
    embed: QueryEmbedder,
    llm: StreamChat,
) -> Iterator[ChatEvent]:
    """Yields events in this order:
    sources -> token... -> done                  (answered)
    [sources ->] no_answer -> done               (not in the documents)
    [sources ->] error                           (LLM unreachable)
    """
    started = time.monotonic()
    usage: dict = {}  # filled by the LLM client with token counts
    with session_factory() as session:
        if conversation_id is None:
            conversation = Conversation(user_id=user_id)
            session.add(conversation)
            session.flush()  # assigns conversation.id
            conversation_id = conversation.id
        question_message = Message(conversation_id=conversation_id, role="user", content=question)
        session.add(question_message)
        session.commit()
        previous = _previous_exchange(session, conversation_id, before_id=question_message.id)
        chunks = _retrieve(session, question, previous, visibilities, embed)

    # Layer 1: nothing similar enough -> answer "not found" without calling the LLM.
    if not chunks:
        yield from _no_answer(session_factory, conversation_id, _metrics(started, usage))
        return

    sources = [{"n": number, **asdict(chunk)} for number, chunk in enumerate(chunks, start=1)]
    yield ChatEvent("sources", {"sources": sources})

    answer = ""
    streaming = False  # becomes True once we know the reply is not the NOT_FOUND marker
    try:
        for piece in llm(SYSTEM_PROMPT, build_user_message(question, chunks, previous), usage=usage):
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
        yield from _no_answer(session_factory, conversation_id, _metrics(started, usage))
        return

    citations = _cited_sources(answer, sources)
    with session_factory() as session:
        message = Message(conversation_id=conversation_id, role="assistant", content=answer.strip(),
                          citations=citations, **_metrics(started, usage))
        session.add(message)
        session.commit()
        yield ChatEvent("done", {"conversation_id": conversation_id, "message_id": message.id,
                                 "citations": citations, "no_answer": False})


def _previous_exchange(session: Session, conversation_id: int, before_id: int) -> tuple[str, str] | None:
    """The question and answer just before this one, if it was answered from the documents."""
    last_two = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.id < before_id)
        .order_by(Message.id.desc())
        .limit(2)
    ).all()
    if len(last_two) == 2:
        answer, question = last_two
        if question.role == "user" and answer.role == "assistant" and not answer.no_answer:
            return question.content, answer.content
    return None


def _retrieve(
    session: Session,
    question: str,
    previous: tuple[str, str] | None,
    visibilities: list[str],
    embed: QueryEmbedder,
) -> list[RetrievedChunk]:
    """Search with the question alone and, for a follow-up, also with the previous
    question in front of it: "can I carry them over?" has no topic of its own.
    Each chunk keeps its best score; then the usual top-k and similarity cutoff apply."""
    queries = [question] + ([f"{previous[0]}\n{question}"] if previous else [])
    best: dict[int, RetrievedChunk] = {}
    for query in queries:
        for chunk in search(session, query, settings.top_k, visibilities, embed=embed):
            if chunk.chunk_id not in best or chunk.score > best[chunk.chunk_id].score:
                best[chunk.chunk_id] = chunk
    ranked = sorted(best.values(), key=lambda chunk: chunk.score, reverse=True)[: settings.top_k]
    return relevant_chunks(ranked, settings.min_similarity)


def _cited_sources(answer: str, sources: list[dict]) -> list[dict]:
    """Only the sources the answer refers to with [n]; numbers the model made up are ignored."""
    cited_numbers = {int(number) for number in re.findall(r"\[(\d+)\]", answer)}
    return [source for source in sources if source["n"] in cited_numbers]


def _metrics(started: float, usage: dict) -> dict:
    """Latency and token counts saved with each answer (shown on the admin page)."""
    metrics = {
        "latency_ms": round((time.monotonic() - started) * 1000),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
    logger.info("answer latency_ms=%(latency_ms)s prompt_tokens=%(prompt_tokens)s "
                "completion_tokens=%(completion_tokens)s", metrics)
    return metrics


def _no_answer(session_factory: sessionmaker, conversation_id: int, metrics: dict) -> Iterator[ChatEvent]:
    with session_factory() as session:
        message = Message(conversation_id=conversation_id, role="assistant", content=NO_ANSWER_MESSAGE,
                          no_answer=True, **metrics)
        session.add(message)
        session.commit()
    yield ChatEvent("no_answer", {"message": NO_ANSWER_MESSAGE, "offer_ticket": True})
    yield ChatEvent("done", {"conversation_id": conversation_id, "message_id": message.id,
                             "citations": [], "no_answer": True})
