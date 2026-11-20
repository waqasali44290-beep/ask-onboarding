"""Routes: POST /api/documents (upload), GET /api/documents, GET /api/documents/{id}, DELETE /api/documents/{id}."""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user, require_role, visible_to
from app.config import settings
from app.db import get_session
from app.ingestion.parsers import ParseError
from app.ingestion.pipeline import ingest_document, register_upload
from app.ingestion.suggestions import generate_quiz, suggest_questions
from app.models import Chunk, Document, User
from app.schemas import DocumentDetail, DocumentOut, DocumentUpdate, Visibility

# Reading needs a login; uploading and deleting are admin-only (per route below).
router = APIRouter(prefix="/api/documents", tags=["documents"])
admin_only = [Depends(require_role("admin"))]


# Plain `def` (not async): FastAPI runs it in a thread pool, so the blocking
# database calls don't freeze other requests.
@router.post("", response_model=DocumentOut, status_code=202, dependencies=admin_only)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    response: Response,
    visibility: Visibility = Form("everyone"),
    session: Session = Depends(get_session),
):
    filename = Path(file.filename or "").name  # drop any folder path the browser sends
    data = file.file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")

    try:
        document, needs_ingestion = register_upload(session, filename, data, visibility)
    except ParseError as exc:
        raise HTTPException(400, str(exc)) from exc

    if needs_ingestion:
        background_tasks.add_task(ingest_document, document.id, filename, data)
        background_tasks.add_task(suggest_questions, document.id)  # runs after ingestion finishes
        background_tasks.add_task(generate_quiz, document.id)
    else:
        response.status_code = 200  # same file already indexed, nothing to do
    return _with_chunk_count(session, document, DocumentOut)


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(current_user), session: Session = Depends(get_session)):
    counts = (
        select(Chunk.document_id, func.count().label("chunk_count"))
        .group_by(Chunk.document_id)
        .subquery()
    )
    rows = session.execute(
        select(Document, func.coalesce(counts.c.chunk_count, 0))
        .outerjoin(counts, counts.c.document_id == Document.id)
        .where(Document.visibility.in_(visible_to(user)))
        .order_by(Document.updated_at.desc())
    )
    return [
        DocumentOut.model_validate(document).model_copy(update={"chunk_count": chunk_count})
        for document, chunk_count in rows
    ]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    return _with_chunk_count(session, _get_or_404(session, document_id, user), DocumentDetail)


@router.patch("/{document_id}", response_model=DocumentOut, dependencies=admin_only)
def update_document(document_id: int, request: DocumentUpdate, session: Session = Depends(get_session)):
    document = _get_or_404(session, document_id)
    document.visibility = request.visibility
    session.commit()
    return _with_chunk_count(session, document, DocumentOut)


@router.delete("/{document_id}", status_code=204, dependencies=admin_only)
def delete_document(document_id: int, session: Session = Depends(get_session)):
    session.delete(_get_or_404(session, document_id))
    session.commit()


def _get_or_404(session: Session, document_id: int, user: User | None = None) -> Document:
    """A document the user may not read looks exactly like a missing one."""
    document = session.get(Document, document_id)
    if document is None or (user is not None and document.visibility not in visible_to(user)):
        raise HTTPException(404, "Document not found.")
    return document


def _with_chunk_count(session: Session, document: Document, schema: type[DocumentOut]) -> DocumentOut:
    chunk_count = session.scalar(select(func.count()).where(Chunk.document_id == document.id))
    return schema.model_validate(document).model_copy(update={"chunk_count": chunk_count})
