"""A help-desk reply becomes a document, so the same question is answered next time."""
import json

from app.api import chat
from tests.conftest import fake_llm, login

QUESTION = "Where can employees park their car at the office?"


def test_published_reply_answers_the_next_person(client, monkeypatch):
    login(client, "employee")
    ticket = client.post("/api/tickets", json={"question": QUESTION}).json()
    login(client, "admin")
    client.patch(f"/api/tickets/{ticket['id']}", json={"status": "resolved", "response": "Employees park in garage P2, level -1."})

    published = client.post(f"/api/tickets/{ticket['id']}/publish").json()

    assert published["document_id"] is not None
    document = client.get(f"/api/documents/{published['document_id']}").json()
    assert document["status"] == "ready" and "garage P2" in document["full_text"]

    login(client, "manager")  # someone else asks the same question
    monkeypatch.setattr(chat, "stream_chat", fake_llm("Park in garage P2, level -1 [1]."))
    response = client.post("/api/chat", json={"question": QUESTION})
    done = json.loads(response.text.strip().split("data: ")[-1])
    assert done["citations"][0]["filename"] == f"help-desk-answer-{ticket['id']}.md"


def test_publish_needs_a_reply_and_an_admin(client):
    ticket = client.post("/api/tickets", json={"question": QUESTION}).json()
    assert client.post(f"/api/tickets/{ticket['id']}/publish").status_code == 400
    login(client, "manager")
    assert client.post(f"/api/tickets/{ticket['id']}/publish").status_code == 403
