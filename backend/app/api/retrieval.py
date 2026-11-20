"""Route: POST /api/retrieve -> top-k matching chunks with scores for a question."""
from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import current_user
from app.config import settings
from app.db import get_session
from app.rag.embeddings import embed_query
from app.rag.retriever import search
from app.schemas import RetrievedChunkOut, RetrieveRequest, RetrieveResponse

router = APIRouter(prefix="/api", tags=["retrieval"], dependencies=[Depends(current_user)])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(request: RetrieveRequest, session: Session = Depends(get_session)):
    """Shows what the assistant would read before answering. Also used for debugging and evaluation."""
    chunks = search(session, request.question, request.top_k or settings.top_k, embed=embed_query)
    results = [RetrievedChunkOut(**asdict(chunk), relevant=chunk.score >= settings.min_similarity) for chunk in chunks]
    return RetrieveResponse(chunks=results, answerable=any(result.relevant for result in results))
