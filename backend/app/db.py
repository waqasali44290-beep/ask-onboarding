"""SQLAlchemy engine and session factory (get_session dependency for routes)."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# pool_pre_ping: test each pooled connection before use, so a restarted
# database doesn't cause "connection closed" errors on the next request.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False keeps loaded attributes usable after commit,
# so a route can commit and then return the object as JSON.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as session:
        yield session
