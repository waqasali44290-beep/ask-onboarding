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

from app.api import chat, documents, retrieval, tickets
from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.ingestion.pipeline import ingest_document, register_upload
from app.main import app
from app.models import Document, User
from app.rag.llm import LLMError

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
            "TRUNCATE documents, chunks, conversations, messages, tickets, users, user_sessions RESTART IDENTITY CASCADE"
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


class FakeLLM:
    """Replays fixed text pieces like a streaming LLM and records every prompt it receives."""

    def __init__(self, pieces: list[str], error: str | None = None):
        self.pieces = pieces
        self.error = error
        self.prompts: list[str] = []

    def __call__(self, system: str, user: str, usage: dict | None = None):
        self.prompts.append(user)
        if self.error:
            raise LLMError(self.error)
        yield from self.pieces
        if usage is not None:  # like Ollama: counts arrive once the stream is complete
            usage.update(prompt_tokens=len(user.split()), completion_tokens=len("".join(self.pieces).split()))


def fake_llm(*pieces: str, error: str | None = None) -> FakeLLM:
    return FakeLLM(list(pieces), error)


TEST_PASSWORD = "test-password"


def login(client: TestClient, username: str) -> None:
    """Log the test client in as one of the users created by the client fixture."""
    response = client.post("/api/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


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
    app.dependency_overrides[chat.get_session_factory] = lambda: session_factory
    monkeypatch.setattr(retrieval, "embed_query", fake_embed_query)
    monkeypatch.setattr(documents, "suggest_questions", lambda document_id: None)  # tests that need it call it directly
    monkeypatch.setattr(documents, "generate_quiz", lambda document_id: None)
    monkeypatch.setattr(tickets, "ingest_document", partial(ingest_document, session_factory=session_factory, embed=fake_embed))
    monkeypatch.setattr(tickets, "suggest_questions", lambda document_id: None)
    monkeypatch.setattr(chat, "embed_query", fake_embed_query)
    # Tests that reach the LLM replace this with fake_llm(...).
    monkeypatch.setattr(chat, "stream_chat", fake_llm(error="no fake LLM set for this test"))
    monkeypatch.setattr(tickets, "stream_chat", fake_llm(error="no fake LLM set for this test"))
    with session_factory() as session:
        for role in ("employee", "manager", "admin"):
            session.add(User(username=role, display_name=f"Test {role}", role=role,
                             password_hash=hash_password(TEST_PASSWORD)))
        session.commit()
    test_client = TestClient(app)
    login(test_client, "admin")
    yield test_client
    app.dependency_overrides.clear()
