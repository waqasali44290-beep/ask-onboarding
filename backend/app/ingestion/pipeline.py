"""Ingest one file: hash -> parse -> chunk -> embed -> replace old chunks -> set status ready/failed."""
import hashlib
import logging
from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import SessionLocal
from app.ingestion.chunker import chunk_text
from app.ingestion.parsers import ParseError, mime_type_for, parse_file
from app.models import Chunk, Document
from app.rag.embeddings import embed_passages

logger = logging.getLogger(__name__)

Embedder = Callable[[list[str]], list[list[float]]]


def register_upload(session: Session, filename: str, data: bytes) -> tuple[Document, bool]:
    """Create or update the document row for an upload.

    Returns (document, needs_ingestion). An identical file that is already
    indexed, or still being indexed, is not processed again.
    Raises ParseError for unsupported types.
    """
    mime_type = mime_type_for(filename)
    content_hash = hashlib.sha256(data).hexdigest()

    document = session.scalar(select(Document).where(Document.filename == filename))
    if document and document.content_hash == content_hash and document.status != "failed":
        return document, False

    if document is None:
        document = Document(filename=filename)
        session.add(document)
    document.mime_type = mime_type
    document.content_hash = content_hash
    # While 'processing', retrieval ignores this document, so a changed file
    # never answers from its old chunks.
    document.status = "processing"
    document.error = None
    session.commit()
    return document, True


def ingest_document(
    document_id: int,
    filename: str,
    data: bytes,
    session_factory: sessionmaker = SessionLocal,
    embed: Embedder = embed_passages,
) -> None:
    """Runs as a background task after the upload response has been sent."""
    with session_factory() as session:
        document = session.get(Document, document_id)
        if document is None:  # deleted while waiting to be processed
            return

        try:
            parsed = parse_file(filename, data)
            pieces = chunk_text(parsed.text, settings.chunk_size, settings.chunk_overlap)
            vectors = embed([piece.content for piece in pieces])

            # Old chunks are deleted and new ones inserted in the same transaction,
            # so the database never holds a mix of two versions of the file.
            session.execute(delete(Chunk).where(Chunk.document_id == document_id))
            session.add_all(
                Chunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=piece.content,
                    start_char=piece.start_char,
                    end_char=piece.end_char,
                    page=parsed.page_for_offset(piece.start_char),
                    embedding=vector,
                )
                for index, (piece, vector) in enumerate(zip(pieces, vectors))
            )
            document.full_text = parsed.text
            document.status = "ready"
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.exception("Ingestion failed for %s", filename)
            document.status = "failed"
            # ParseError messages are written for users; anything else might leak internals.
            document.error = str(exc) if isinstance(exc, ParseError) else "Unexpected error while processing the file."
            session.commit()
