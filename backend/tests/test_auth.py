"""Login, logout, roles and that users can't see each other's conversations."""
import json

from fastapi.testclient import TestClient

from app.api import chat
from app.main import app
from tests.conftest import fake_llm, login


def test_routes_need_a_login(client):
    anonymous = TestClient(app)
    assert anonymous.get("/api/documents").status_code == 401
    assert anonymous.post("/api/chat", json={"question": "hi"}).status_code == 401
    assert anonymous.get("/api/health").status_code == 200  # health check stays public


def test_login_logout_and_wrong_password(client):
    me = client.get("/api/auth/me").json()
    assert (me["username"], me["role"]) == ("admin", "admin")
    assert "password_hash" not in me

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Wrong username or password."


def test_only_admins_can_upload_or_delete_documents(client):
    document_id = client.post("/api/documents", files={"file": ("a.md", b"Hello")}).json()["id"]
    login(client, "employee")

    assert client.post("/api/documents", files={"file": ("b.md", b"Hi")}).status_code == 403
    assert client.delete(f"/api/documents/{document_id}").status_code == 403
    assert client.get("/api/documents").status_code == 200  # reading is fine


def test_conversations_are_private(client, monkeypatch):
    client.post("/api/documents", files={"file": ("pto.md", b"New employees get 25 days of paid time off.")})
    monkeypatch.setattr(chat, "stream_chat", fake_llm("25 days [1]."))
    login(client, "employee")
    response = client.post("/api/chat", json={"question": "How many days of paid time off do new employees get?"})
    conversation_id = json.loads(response.text.strip().split("data: ")[-1])["conversation_id"]

    login(client, "manager")
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.get("/api/conversations").json() == []
    assert client.post("/api/chat", json={"question": "more?", "conversation_id": conversation_id}).status_code == 404
