"""Settings loaded from environment variables (.env), with defaults for local runs."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    llm_max_tokens: int = 512  # longest answer the model may write
    llm_context_tokens: int = 4096  # prompt + answer must fit; Ollama's default is smaller

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

    demo_password: str = "onboarding"  # password of the demo accounts created on first start
    session_days: int = 7


settings = Settings()
