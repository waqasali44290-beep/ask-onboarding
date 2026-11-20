"""Off-topic question -> no LLM guess, a plain 'not in the documents' reply plus a ticket offer."""
from app.rag.answerer import answer_question
from app.rag.prompts import NO_ANSWER_MESSAGE
from tests.conftest import fake_embed_query, fake_llm, upload

PTO_POLICY = b"New employees get 25 days of paid time off per year."


def ask(session_factory, question: str, llm) -> list:
    return list(answer_question(session_factory, question, None, None, ["everyone"], embed=fake_embed_query, llm=llm))


def test_unrelated_question_is_answered_without_calling_the_llm(session_factory):
    upload(session_factory, "pto.md", PTO_POLICY)
    llm = fake_llm("Paris is the capital of France.")

    events = ask(session_factory, "What is the capital of France?", llm)

    assert llm.prompts == []  # the model never got the chance to guess
    assert [event.name for event in events] == ["no_answer", "done"]
    assert events[0].data == {"message": NO_ANSWER_MESSAGE, "offer_ticket": True}
    assert events[1].data["no_answer"] is True


def test_llm_saying_not_found_becomes_the_no_answer_message(session_factory):
    upload(session_factory, "pto.md", PTO_POLICY)
    # Related source is retrieved, but the model decides it doesn't answer the question.
    llm = fake_llm("NOT", "_FO", "UND")

    events = ask(session_factory, "How many days of paid time off for parental leave?", llm)

    assert len(llm.prompts) == 1
    names = [event.name for event in events]
    assert names == ["sources", "no_answer", "done"]
    assert "token" not in names  # the raw marker is never shown to the user


def test_marker_after_some_text_still_counts_as_no_answer(session_factory):
    upload(session_factory, "pto.md", PTO_POLICY)
    llm = fake_llm("The sources don't mention parental leave. ", "NOT_FOUND")

    events = ask(session_factory, "How many days of paid time off for parental leave?", llm)

    assert events[-2].name == "no_answer"


def test_with_no_documents_at_all_the_assistant_says_so(session_factory):
    events = ask(session_factory, "How many days of paid time off?", fake_llm("25 days."))
    assert events[0].name == "no_answer"
