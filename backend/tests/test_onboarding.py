"""Onboarding journey: checklist per role, progress, and a quiz from the documents."""
from app.ingestion.suggestions import generate_quiz, parse_quiz
from tests.conftest import fake_llm, login

QUIZ_REPLY = "Q: How many PTO days do new employees get?\nA) 10\nB) 25\nC) 30\nD) 40\nAnswer: B"


def test_parse_quiz_accepts_the_format_and_rejects_anything_else():
    assert parse_quiz(QUIZ_REPLY) == {"question": "How many PTO days do new employees get?",
                                      "options": ["10", "25", "30", "40"], "answer": 1}
    assert parse_quiz("Q: Missing options?\nA) yes\nAnswer: A") is None
    assert parse_quiz("Here is a question about PTO.") is None


def test_checklist_depends_on_role_and_tracks_progress(client):
    login(client, "employee")
    tasks = client.get("/api/onboarding").json()["tasks"]
    assert "salary-bands" not in [t["id"] for t in tasks]
    assert not any(t["done"] for t in tasks)

    assert client.put("/api/onboarding/tasks/vpn", json={"done": True}).status_code == 204
    assert client.put("/api/onboarding/tasks/vpn", json={"done": True}).status_code == 204  # twice is fine
    assert [t["id"] for t in client.get("/api/onboarding").json()["tasks"] if t["done"]] == ["vpn"]
    client.put("/api/onboarding/tasks/vpn", json={"done": False})
    assert not any(t["done"] for t in client.get("/api/onboarding").json()["tasks"])

    assert client.put("/api/onboarding/tasks/salary-bands", json={"done": True}).status_code == 404
    login(client, "manager")
    assert "salary-bands" in [t["id"] for t in client.get("/api/onboarding").json()["tasks"]]


def test_quiz_comes_from_readable_documents_and_keeps_the_best_score(client, session_factory):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off.")})
    client.post("/api/documents", files={"file": ("salary.md", b"Bands are secret.")}, data={"visibility": "managers"})
    generate_quiz(1, session_factory, llm=fake_llm(QUIZ_REPLY))
    generate_quiz(2, session_factory, llm=fake_llm(QUIZ_REPLY.replace("PTO days", "salary band")))
    login(client, "employee")

    quiz = client.get("/api/onboarding/quiz?count=10").json()
    assert [(q["filename"], q["answer"]) for q in quiz] == [("pto.md", 1)]  # nothing from the managers-only doc

    assert client.post("/api/onboarding/quiz", json={"correct": 4, "total": 5}).json()["quiz_best"] == 80
    assert client.post("/api/onboarding/quiz", json={"correct": 1, "total": 5}).json()["quiz_best"] == 80
    assert client.post("/api/onboarding/quiz", json={"correct": 6, "total": 5}).status_code == 422
