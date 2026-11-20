"""Follow-up questions use the previous question to find the right sources."""
import json

from app.api import chat
from tests.conftest import fake_llm, login


def ask(client, question: str, conversation_id: int | None = None) -> tuple[list[str], dict]:
    response = client.post("/api/chat", json={"question": question, "conversation_id": conversation_id})
    events = [block.split("\n")[0].removeprefix("event: ") for block in response.text.strip().split("\n\n")]
    return events, json.loads(response.text.strip().split("data: ")[-1])


def test_follow_up_without_a_topic_finds_sources_through_the_previous_question(client, monkeypatch):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off per year.")})
    llm = fake_llm("Yes [1].")
    monkeypatch.setattr(chat, "stream_chat", llm)
    login(client, "employee")

    _, first = ask(client, "How many days of paid time off do new employees get?")
    events, _ = ask(client, "What about after that?", first["conversation_id"])  # shares no words with the doc

    assert "no_answer" not in events
    assert "<earlier_conversation" in llm.prompts[1]
    assert "Employee: How many days of paid time off do new employees get?" in llm.prompts[1]
    assert "<earlier_conversation" not in llm.prompts[0]  # first questions get the plain prompt


def test_same_words_in_a_new_conversation_get_no_answer(client, monkeypatch):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off per year.")})
    monkeypatch.setattr(chat, "stream_chat", fake_llm("Yes [1]."))
    login(client, "employee")

    events, _ = ask(client, "What about after that?")

    assert "no_answer" in events
