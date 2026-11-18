"""Vector search in pgvector: return the top-k chunks most similar to a question."""
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.rag.embeddings import embed_query

QueryEmbedder = Callable[[str], list[float]]


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    content: str
    start_char: int
    end_char: int
    page: int | None
    score: float  # cosine similarity: 1.0 = same meaning, ~0.4 = unrelated (for bge-small)


def search(session: Session, question: str, top_k: int, embed: QueryEmbedder = embed_query) -> list[RetrievedChunk]:
    """Best-matching chunks first. Only documents with status 'ready' are searched,
    so a file that is being re-processed never answers from its old version."""
    # pgvector's <=> operator: cosine distance = 1 - cosine similarity.
    distance = Chunk.embedding.cosine_distance(embed(question)).label("distance")
    rows = session.execute(
        select(Chunk, Document.filename, distance)
        .join(Document)
        .where(Document.status == "ready")
        .order_by(distance)
        .limit(top_k)
    )
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            content=chunk.content,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            page=chunk.page,
            score=round(1 - chunk_distance, 4),
        )
        for chunk, filename, chunk_distance in rows
    ]


def relevant_chunks(chunks: list[RetrievedChunk], min_similarity: float) -> list[RetrievedChunk]:
    """Chunks similar enough to be worth showing the LLM. Empty list = 'not in the documents'."""
    return [chunk for chunk in chunks if chunk.score >= min_similarity]
