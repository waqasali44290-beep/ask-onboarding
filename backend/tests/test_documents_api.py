"""HTTP behaviour of the /api/documents endpoints."""


def test_upload_returns_processing_then_document_becomes_ready(client):
    response = client.post("/api/documents", files={"file": ("it/vpn.txt", b"Connect to the VPN before using Jira.")})
    assert response.status_code == 202
    assert response.json()["status"] == "processing"
    assert response.json()["filename"] == "vpn.txt"  # folder path stripped

    # TestClient runs background tasks before returning, so ingestion is done.
    [document] = client.get("/api/documents").json()
    assert document["status"] == "ready"
    assert document["chunk_count"] == 1

    detail = client.get(f"/api/documents/{document['id']}").json()
    assert detail["full_text"] == "Connect to the VPN before using Jira."


def test_unsupported_file_type_is_a_400(client):
    response = client.post("/api/documents", files={"file": ("deck.pptx", b"...")})
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_missing_document_is_a_404_and_delete_removes_it(client):
    assert client.get("/api/documents/999").status_code == 404

    document_id = client.post("/api/documents", files={"file": ("a.md", b"Hello")}).json()["id"]
    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get("/api/documents").json() == []
