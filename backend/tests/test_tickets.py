"""Creating a ticket saves title, question and user, and it appears in GET /api/tickets."""
import json

from app.api import chat
from tests.conftest import fake_llm


def test_unanswered_question_can_become_a_ticket_and_is_listed(client, monkeypatch):
    # The real flow: a question the documents can't answer...
    monkeypatch.setattr(chat, "stream_chat", fake_llm("NOT_FOUND"))
    response = client.post("/api/chat", json={"question": "Where do I park my car?"})
    done = json.loads(response.text.strip().split("\n\n")[-1].split("data: ")[1])
    assert done["no_answer"] is True

    # ...then the user clicks "Yes, open a ticket".
    created = client.post("/api/tickets", json={
        "question": "Where do I park my car?",
        "user_name": "Ali",
        "conversation_id": done["conversation_id"],
    })

    assert created.status_code == 201
    ticket = created.json()
    assert ticket["title"] == "Where do I park my car?"  # defaults to the question
    assert ticket["user_name"] == "Ali"
    assert ticket["status"] == "open"
    assert client.get("/api/tickets").json() == [ticket]


def test_long_question_gets_a_short_title_and_newest_ticket_is_listed_first(client):
    long_question = "How do I request a standing desk and a second monitor for my home office " * 3
    client.post("/api/tickets", json={"question": "First question?", "user_name": "Sara"})
    client.post("/api/tickets", json={"question": long_question, "user_name": "Ali"})

    newest, oldest = client.get("/api/tickets").json()

    assert oldest["title"] == "First question?"
    assert newest["title"].endswith("…") and len(newest["title"]) <= 81
    assert newest["question"] == long_question.strip()


def test_ticket_needs_a_question_and_a_user(client):
    assert client.post("/api/tickets", json={"question": "Parking?", "user_name": " "}).status_code == 422
    assert client.post("/api/tickets", json={"question": "", "user_name": "Ali"}).status_code == 422
    assert client.post("/api/tickets", json={"question": "Parking?", "user_name": "Ali",
                                             "conversation_id": 999}).status_code == 404
