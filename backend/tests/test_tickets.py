"""Tickets: created from unanswered questions, private to their owner, managed by admins."""
import json

from app.api import chat, tickets
from tests.conftest import fake_llm, login


def open_ticket(client, question: str = "Where do I park my car?") -> dict:
    response = client.post("/api/tickets", json={"question": question})
    assert response.status_code == 201, response.text
    return response.json()


def test_unanswered_question_can_become_a_ticket(client, monkeypatch):
    login(client, "employee")
    # The real flow: a question the documents can't answer...
    monkeypatch.setattr(chat, "stream_chat", fake_llm("NOT_FOUND"))
    response = client.post("/api/chat", json={"question": "Where do I park my car?"})
    done = json.loads(response.text.strip().split("\n\n")[-1].split("data: ")[1])
    assert done["no_answer"] is True

    # ...then the user confirms the suggested ticket.
    ticket = client.post("/api/tickets", json={
        "question": "Where do I park my car?",
        "title": "Parking information request",
        "conversation_id": done["conversation_id"],
    }).json()

    assert ticket["title"] == "Parking information request"
    assert ticket["user_name"] == "Test employee"  # taken from the login
    assert (ticket["status"], ticket["response"]) == ("open", None)


def test_title_defaults_to_the_question_shortened(client):
    ticket = open_ticket(client, "How do I request a standing desk and a second monitor for my home office " * 3)
    assert ticket["title"].endswith("…") and len(ticket["title"]) <= 81


def test_employees_only_see_their_own_tickets_admins_see_all(client):
    login(client, "employee")
    mine = open_ticket(client)
    login(client, "manager")
    open_ticket(client, "Is there a gym?")

    assert [t["id"] for t in client.get("/api/tickets").json()] == [2]  # manager sees only theirs
    login(client, "admin")
    assert [t["id"] for t in client.get("/api/tickets").json()] == [2, mine["id"]]
    assert [t["id"] for t in client.get("/api/tickets?status=open").json()] == [2, mine["id"]]


def test_admin_replies_and_resolves(client):
    login(client, "employee")
    ticket = open_ticket(client)

    login(client, "admin")
    client.patch(f"/api/tickets/{ticket['id']}", json={"status": "in_progress"})
    resolved = client.patch(f"/api/tickets/{ticket['id']}",
                            json={"status": "resolved", "response": "Use the P2 garage, level -1."}).json()
    assert resolved["status"] == "resolved" and resolved["resolved_at"] is not None
    assert client.get("/api/tickets?status=resolved").json()[0]["response"] == "Use the P2 garage, level -1."

    login(client, "employee")
    assert client.get("/api/tickets").json()[0]["response"] == "Use the P2 garage, level -1."


def test_owner_can_only_close_and_others_cannot_touch_it(client):
    login(client, "employee")
    ticket = open_ticket(client)
    url = f"/api/tickets/{ticket['id']}"

    assert client.patch(url, json={"status": "in_progress"}).status_code == 403
    assert client.patch(url, json={"response": "fixed it myself"}).status_code == 403
    login(client, "manager")
    assert client.patch(url, json={"status": "resolved"}).status_code == 404  # not theirs
    login(client, "employee")
    assert client.patch(url, json={"status": "resolved"}).json()["status"] == "resolved"


def test_validation(client):
    assert client.post("/api/tickets", json={"question": ""}).status_code == 422
    assert client.post("/api/tickets", json={"question": "Parking?", "conversation_id": 999}).status_code == 404
    assert client.patch(f"/api/tickets/{open_ticket(client)['id']}", json={"status": "closed"}).status_code == 422


def test_draft_suggests_a_title_from_the_llm(client, monkeypatch):
    monkeypatch.setattr(tickets, "stream_chat", fake_llm('"Request for parking information at the office"\nThanks!'))
    draft = client.post("/api/tickets/draft", json={"question": "where do i park"}).json()
    assert draft == {"title": "Request for parking information at the office"}  # quotes and extra line removed


def test_draft_falls_back_to_the_question_when_the_llm_is_down(client, monkeypatch):
    monkeypatch.setattr(tickets, "stream_chat", fake_llm(error="connection refused"))
    draft = client.post("/api/tickets/draft", json={"question": "Where do I park my car?"}).json()
    assert draft == {"title": "Where do I park my car?"}
