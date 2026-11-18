"""Settings loaded from environment variables (.env). The API key never leaves the server."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"
    llm_max_tokens: int = 1024

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_cache_dir: str = "/root/.cache/fastembed"

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    min_similarity: float = 0.50

    database_url: str = "postgresql+psycopg://ask:ask@localhost:5432/ask_onboarding"
    max_upload_mb: int = 20
    cors_origins: str = "http://localhost:5173"


settings = Settings()
