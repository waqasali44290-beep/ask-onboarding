"""Re-uploading a changed file removes old chunks; answers only use the new version."""
from sqlalchemy import select

from app.ingestion.pipeline import ingest_document, register_upload
from app.models import Chunk, Document
from tests.conftest import fake_embed


def upload(session_factory, filename: str, data: bytes) -> tuple[Document, bool]:
    """Register and ingest a file the same way the upload endpoint does."""
    with session_factory() as session:
        document, needs_ingestion = register_upload(session, filename, data)
    if needs_ingestion:
        ingest_document(document.id, filename, data, session_factory=session_factory, embed=fake_embed)
    with session_factory() as session:
        return session.get(Document, document.id), needs_ingestion


def chunk_texts(session_factory, document_id: int) -> list[str]:
    with session_factory() as session:
        return list(session.scalars(select(Chunk.content).where(Chunk.document_id == document_id)))


def test_first_upload_is_indexed_and_ready(session_factory):
    document, _ = upload(session_factory, "pto.md", b"New employees get 20 days of PTO.")
    assert document.status == "ready"
    assert chunk_texts(session_factory, document.id) == ["New employees get 20 days of PTO."]


def test_changed_file_replaces_all_old_chunks(session_factory):
    first, _ = upload(session_factory, "pto.md", b"New employees get 20 days of PTO.")
    second, needs_ingestion = upload(session_factory, "pto.md", b"New employees get 25 days of PTO.")

    assert needs_ingestion
    assert second.id == first.id  # same document, new content
    chunks = chunk_texts(session_factory, second.id)
    assert chunks == ["New employees get 25 days of PTO."]
    assert not any("20 days" in chunk for chunk in chunks)
    assert "25 days" in second.full_text


def test_identical_reupload_is_skipped(session_factory):
    upload(session_factory, "pto.md", b"New employees get 20 days of PTO.")
    with session_factory() as session:
        chunk_ids_before = list(session.scalars(select(Chunk.id)))

    _, needs_ingestion = upload(session_factory, "pto.md", b"New employees get 20 days of PTO.")

    with session_factory() as session:
        assert not needs_ingestion
        assert list(session.scalars(select(Chunk.id))) == chunk_ids_before


def test_identical_upload_while_still_processing_is_not_ingested_twice(session_factory):
    with session_factory() as session:
        _, first_needs_ingestion = register_upload(session, "pto.md", b"20 days of PTO.")
        _, second_needs_ingestion = register_upload(session, "pto.md", b"20 days of PTO.")
    assert first_needs_ingestion
    assert not second_needs_ingestion


def test_unreadable_file_is_marked_failed_with_a_reason(session_factory):
    document, _ = upload(session_factory, "broken.pdf", b"not really a pdf")
    assert document.status == "failed"
    assert "Could not read the PDF" in document.error
    assert chunk_texts(session_factory, document.id) == []
