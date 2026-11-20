"""Admin stats: latency, tokens, cost, feedback and no-answer numbers."""
import json

from app.api import chat
from app.config import settings
from tests.conftest import fake_llm, login


def ask(client, question: str) -> dict:
    response = client.post("/api/chat", json={"question": question})
    return json.loads(response.text.strip().split("data: ")[-1])


def test_stats_count_answers_tokens_cost_and_feedback(client, monkeypatch):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off per year.")})
    monkeypatch.setattr(chat, "stream_chat", fake_llm("You get 25 days [1]."))
    monkeypatch.setattr(settings, "llm_cost_per_million_input_tokens", 1.0)
    login(client, "employee")
    answered = ask(client, "How many days of paid time off do new employees get?")
    ask(client, "What is the capital of France?")  # below the cutoff -> no answer
    client.post(f"/api/messages/{answered['message_id']}/feedback", json={"rating": -1})
    client.post("/api/tickets", json={"question": "What is the capital of France?"})

    login(client, "admin")
    stats = client.get("/api/admin/stats").json()

    assert (stats["answers"], stats["no_answers"], stats["no_answer_rate"]) == (2, 1, 0.5)
    assert (stats["thumbs_up"], stats["thumbs_down"]) == (0, 1)
    assert stats["tickets"] == {"open": 1}
    assert stats["prompt_tokens"] > 0 and stats["completion_tokens"] == 5
    assert stats["total_cost_usd"] == stats["prompt_tokens"] / 1_000_000

    newest, oldest = stats["recent"]
    assert newest["no_answer"] and newest["question"] == "What is the capital of France?"
    assert oldest["user_name"] == "Test employee" and oldest["feedback"] == -1
    assert oldest["latency_ms"] is not None


def test_stats_are_admin_only(client):
    login(client, "manager")
    assert client.get("/api/admin/stats").status_code == 403
