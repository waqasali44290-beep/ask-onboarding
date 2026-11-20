"""Knowledge-gap radar."""
from app.api import admin
from app.rag.gaps import find_gaps
from tests.conftest import fake_embed, login


def test_similar_questions_are_grouped_biggest_first():
    questions = [
        "where do I park my car",
        "what is the dress code",
        "where can I park my car",
        "where do I park my bike",
        "where do I park my car",
    ]
    gaps = find_gaps(questions, fake_embed, threshold=0.7)
    assert [len(g.questions) for g in gaps] == [4, 1]
    assert gaps[0].topic == "where do I park my car"
    assert find_gaps([], fake_embed) == []


def test_gaps_endpoint_uses_unanswered_and_waiting_questions(client, monkeypatch):
    monkeypatch.setattr(admin, "embed_passages", fake_embed)
    login(client, "employee")
    client.post("/api/chat", json={"question": "where do I park my car"})  # no documents -> no answer
    client.post("/api/tickets", json={"question": "where can I park my car"})
    login(client, "admin")

    gaps = client.get("/api/admin/gaps").json()

    assert gaps[0]["count"] == 2
    assert set(gaps[0]["examples"]) == {"where do I park my car", "where can I park my car"}
    login(client, "manager")
    assert client.get("/api/admin/gaps").status_code == 403
