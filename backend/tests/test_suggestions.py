"""Suggested questions: written per document by the LLM, shown under answers and on the welcome screen."""
import json

from app.api import chat
from app.ingestion.suggestions import parse_questions, suggest_questions
from tests.conftest import fake_llm, login, upload


def test_parse_keeps_only_clean_questions():
    reply = '1. How many PTO days do I get?\n- "Can I carry days over?"\nHere are some ideas:\nWho approves leave?\nWhat else?'
    assert parse_questions(reply) == ["How many PTO days do I get?", "Can I carry days over?", "Who approves leave?"]


def test_suggestions_are_stored_and_llm_failures_are_harmless(session_factory):
    good, _ = upload(session_factory, "pto.md", b"New employees get 25 days of paid time off per year.")
    other, _ = upload(session_factory, "vpn.md", b"Install WireGuard to reach Jira from home.")

    suggest_questions(good.id, session_factory, llm=fake_llm("How many PTO days do I get?"))
    suggest_questions(other.id, session_factory, llm=fake_llm(error="down"))

    with session_factory() as session:
        from app.models import Document
        assert session.get(Document, good.id).suggested_questions == ["How many PTO days do I get?"]
        assert session.get(Document, other.id).suggested_questions == []


def test_answers_come_with_related_questions_and_welcome_screen_respects_access(client, session_factory, monkeypatch):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off per year.")})
    client.post("/api/documents", files={"file": ("salary.md", b"Salary bands are confidential.")},
                data={"visibility": "managers"})
    llm = fake_llm("How many days of paid time off do new employees get?\nCan I carry PTO days over?")
    suggest_questions(1, session_factory, llm=llm)
    suggest_questions(2, session_factory, llm=fake_llm("What are the salary bands?"))
    monkeypatch.setattr(chat, "stream_chat", fake_llm("25 days [1]."))
    login(client, "employee")

    response = client.post("/api/chat", json={"question": "How many days of paid time off do new employees get?"})
    done = json.loads(response.text.strip().split("data: ")[-1])

    assert done["suggestions"] == ["Can I carry PTO days over?"]  # the asked question itself is skipped
    welcome = client.get("/api/suggestions?limit=10").json()
    assert sorted(welcome) == ["Can I carry PTO days over?", "How many days of paid time off do new employees get?"]  # no salary question
