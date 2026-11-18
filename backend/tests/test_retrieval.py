"""The right chunk ranks first for a known question; results are capped at top_k."""
from app.ingestion.pipeline import register_upload
from app.rag.retriever import RetrievedChunk, relevant_chunks, search
from tests.conftest import fake_embed_query, upload


def add_handbook(session_factory):
    upload(session_factory, "pto.md", b"New employees get 25 days of paid time off per year.")
    upload(session_factory, "vpn.txt", b"Connect to the VPN before using Jira or the wiki.")
    upload(session_factory, "lost-device.txt", b"Report a lost laptop to the IT help desk within 24 hours.")


def test_most_relevant_chunk_ranks_first(session_factory):
    add_handbook(session_factory)
    with session_factory() as session:
        results = search(session, "How do I report a lost laptop?", top_k=3, embed=fake_embed_query)

    assert results[0].filename == "lost-device.txt"
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)


def test_results_are_capped_at_top_k(session_factory):
    add_handbook(session_factory)
    with session_factory() as session:
        assert len(search(session, "laptop", top_k=2, embed=fake_embed_query)) == 2


def test_document_being_reprocessed_is_not_searched(session_factory):
    upload(session_factory, "pto.md", b"New employees get 20 days of paid time off.")
    with session_factory() as session:
        # A changed version arrives: old chunks still exist until ingestion finishes...
        register_upload(session, "pto.md", b"New employees get 25 days of paid time off.")
        # ...but they must not be used to answer.
        assert search(session, "paid time off", top_k=5, embed=fake_embed_query) == []


def test_relevant_chunks_drops_low_scores():
    def chunk(score: float) -> RetrievedChunk:
        return RetrievedChunk(1, 1, "a.md", "text", 0, 4, None, score)

    assert [c.score for c in relevant_chunks([chunk(0.8), chunk(0.49), chunk(0.5)], 0.5)] == [0.8, 0.5]
    assert relevant_chunks([chunk(0.3)], 0.5) == []


def test_retrieve_endpoint_returns_scored_chunks_with_citation_offsets(client):
    client.post("/api/documents", files={"file": ("vpn.txt", b"Connect to the VPN before using Jira.")})

    body = client.post("/api/retrieve", json={"question": "VPN Jira"}).json()

    assert body["answerable"] is True
    [chunk] = body["chunks"]
    assert chunk["filename"] == "vpn.txt"
    assert chunk["relevant"] is True
    assert (chunk["start_char"], chunk["end_char"]) == (0, len("Connect to the VPN before using Jira."))


def test_unrelated_question_is_not_answerable(client):
    client.post("/api/documents", files={"file": ("vpn.txt", b"Connect to the VPN before using Jira.")})

    body = client.post("/api/retrieve", json={"question": "What is the capital of France?"}).json()

    assert body["answerable"] is False
    assert not any(chunk["relevant"] for chunk in body["chunks"])


def test_blank_question_and_bad_top_k_are_rejected(client):
    assert client.post("/api/retrieve", json={"question": "   "}).status_code == 422
    assert client.post("/api/retrieve", json={"question": "vpn", "top_k": 0}).status_code == 422
