"""Wrapper around the local fastembed model: turns text into vectors for pgvector."""
from functools import lru_cache

from fastembed import TextEmbedding

from app.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # Loaded once per process. The first call downloads the model (~130 MB)
    # into cache_dir, which docker-compose mounts as a volume so it survives restarts.
    return TextEmbedding(model_name=settings.embedding_model, cache_dir=settings.embedding_cache_dir)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed document chunks."""
    return [vector.tolist() for vector in _model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embed a user question. BGE models add a search instruction to queries,
    which is why questions and passages go through different methods."""
    return next(iter(_model().query_embed(text))).tolist()
