"""Shared fixtures: test database, fake embedder, fake LLM (tests never call the real API)."""
import hashlib
import math
import re
from functools import partial
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.api import documents, retrieval
from app.config import settings
from app.db import get_session
from app.ingestion.pipeline import ingest_document, register_upload
from app.main import app
from app.models import Document

TEST_DATABASE = "ask_onboarding_test"
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "db" / "init.sql"


@pytest.fixture(scope="session")
def engine():
    """A fresh test database built from db/init.sql, so tests never touch real data."""
    url = make_url(settings.database_url)
    # CREATE/DROP DATABASE can't run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)")
        connection.exec_driver_sql(f"CREATE DATABASE {TEST_DATABASE}")
    admin_engine.dispose()

    test_engine = create_engine(url.set(database=TEST_DATABASE))
    with test_engine.begin() as connection:
        connection.exec_driver_sql(SCHEMA_FILE.read_text())
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    """Session factory for the test database; every table is emptied after each test."""
    yield sessionmaker(bind=engine, expire_on_commit=False)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE documents, chunks, conversations, messages, tickets RESTART IDENTITY CASCADE"
        )


def fake_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic stand-in for the real model: a normalised bag-of-words vector.

    Texts that share words get similar vectors, which is enough to test
    ingestion and retrieval logic without downloading a model.
    """
    vectors = []
    for text in texts:
        vector = [0.0] * settings.embedding_dim
        for word in re.findall(r"\w+", text.lower()):
            # md5 instead of hash(): Python's hash() changes between runs.
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % settings.embedding_dim
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        vectors.append([value / norm for value in vector])
    return vectors


def fake_embed_query(text: str) -> list[float]:
    return fake_embed([text])[0]


def upload(session_factory, filename: str, data: bytes) -> tuple[Document, bool]:
    """Register and ingest a file the same way the upload endpoint does."""
    with session_factory() as session:
        document, needs_ingestion = register_upload(session, filename, data)
    if needs_ingestion:
        ingest_document(document.id, filename, data, session_factory=session_factory, embed=fake_embed)
    with session_factory() as session:
        return session.get(Document, document.id), needs_ingestion


@pytest.fixture
def client(session_factory, monkeypatch):
    """API client wired to the test database and the fake embedders."""

    def test_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    monkeypatch.setattr(
        documents, "ingest_document",
        partial(ingest_document, session_factory=session_factory, embed=fake_embed),
    )
    monkeypatch.setattr(retrieval, "embed_query", fake_embed_query)
    yield TestClient(app)
    app.dependency_overrides.clear()
