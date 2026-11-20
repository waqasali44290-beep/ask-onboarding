"""Thumbs up / down on answers."""
import json

from app.api import chat
from tests.conftest import fake_llm, login


def ask(client, monkeypatch) -> dict:
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off per year.")})
    monkeypatch.setattr(chat, "stream_chat", fake_llm("25 days [1]."))
    login(client, "employee")
    response = client.post("/api/chat", json={"question": "How many days of paid time off do new employees get?"})
    return json.loads(response.text.strip().split("data: ")[-1])


def test_rating_is_saved_changed_and_removed(client, monkeypatch):
    done = ask(client, monkeypatch)
    url = f"/api/messages/{done['message_id']}/feedback"
    history = f"/api/conversations/{done['conversation_id']}"

    assert client.post(url, json={"rating": 1}).status_code == 204
    assert client.get(history).json()["messages"][1]["feedback"] == 1
    client.post(url, json={"rating": -1})
    assert client.get(history).json()["messages"][1]["feedback"] == -1
    client.post(url, json={"rating": 0})
    assert client.get(history).json()["messages"][1]["feedback"] is None


def test_only_the_owner_can_rate_and_only_answers(client, monkeypatch):
    done = ask(client, monkeypatch)
    question_id = done["message_id"] - 1  # the user message just before the answer

    assert client.post(f"/api/messages/{question_id}/feedback", json={"rating": 1}).status_code == 404
    assert client.post(f"/api/messages/{done['message_id']}/feedback", json={"rating": 5}).status_code == 422
    login(client, "manager")
    assert client.post(f"/api/messages/{done['message_id']}/feedback", json={"rating": 1}).status_code == 404
