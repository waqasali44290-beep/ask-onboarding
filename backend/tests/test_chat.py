"""Answer streaming, citations, LLM failures and conversation history over HTTP."""
import json

from app.api import chat
from app.config import settings
from app.rag.answerer import LLM_UNAVAILABLE_MESSAGE
from tests.conftest import fake_llm

PTO_POLICY = ("pto.md", b"New employees get 25 days of paid time off per year.")
VPN_GUIDE = ("vpn.txt", b"Connect to the VPN before using Jira. New employees get VPN access on day one.")


def post_chat(client, question: str, conversation_id: int | None = None) -> list[tuple[str, dict]]:
    """Send a question and parse the Server-Sent Events stream into (name, data) pairs."""
    response = client.post("/api/chat", json={"question": question, "conversation_id": conversation_id})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append((name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


def test_answer_streams_tokens_and_returns_only_the_cited_sources(client, monkeypatch):
    for file in (PTO_POLICY, VPN_GUIDE):
        client.post("/api/documents", files={"file": file})
    # Low cutoff so both files reach the LLM; the answer then cites only one of them.
    monkeypatch.setattr(settings, "min_similarity", 0.1)
    llm = fake_llm("New employees get ", "25 days of paid time off [1].")
    monkeypatch.setattr(chat, "stream_chat", llm)

    events = post_chat(client, "How many days of paid time off do new employees get?")

    names = [name for name, _ in events]
    assert names[0] == "sources" and names[-1] == "done"
    assert "".join(data["text"] for name, data in events if name == "token") == \
        "New employees get 25 days of paid time off [1]."

    sources = events[0][1]["sources"]
    assert len(sources) == 2  # both files were relevant enough to send...
    assert "<source id=\"1\" file=\"pto.md\">" in llm.prompts[0]
    [citation] = events[-1][1]["citations"]  # ...but only the cited one is returned
    assert citation["filename"] == "pto.md"
    assert (citation["start_char"], citation["end_char"]) == (0, len(PTO_POLICY[1]))


def test_conversation_history_is_saved_and_continues(client, monkeypatch):
    client.post("/api/documents", files={"file": PTO_POLICY})
    monkeypatch.setattr(chat, "stream_chat", fake_llm("You get 25 days [1]."))

    first = post_chat(client, "How many days of paid time off do new employees get?")
    conversation_id = first[-1][1]["conversation_id"]
    post_chat(client, "Is it paid time off per year?", conversation_id)

    history = client.get(f"/api/conversations/{conversation_id}").json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant", "user", "assistant"]
    assert history["messages"][1]["citations"][0]["filename"] == "pto.md"


def test_llm_outage_gives_a_friendly_error_event(client, monkeypatch):
    client.post("/api/documents", files={"file": PTO_POLICY})
    monkeypatch.setattr(chat, "stream_chat", fake_llm(error="connection refused"))

    events = post_chat(client, "How many days of paid time off do new employees get?")

    assert events[-1] == ("error", {"message": LLM_UNAVAILABLE_MESSAGE})


def test_unknown_conversation_and_blank_question_are_rejected(client):
    assert client.post("/api/chat", json={"question": "hi", "conversation_id": 999}).status_code == 404
    assert client.post("/api/chat", json={"question": "  "}).status_code == 422
    assert client.get("/api/conversations/999").status_code == 404
