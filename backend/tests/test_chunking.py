"""Chunk size/overlap respected, offsets map back to the original text, no empty chunks."""
import pytest

from app.ingestion.chunker import chunk_text

PARAGRAPH = (
    "New employees get 25 days of paid time off per year. "
    "Unused days can be carried over until the end of March. "
    "Requests go through the HR portal and need manager approval.\n\n"
)
LONG_TEXT = PARAGRAPH * 20


def test_offsets_point_back_to_the_exact_source_text():
    for chunk in chunk_text(LONG_TEXT, chunk_size=200, overlap=40):
        assert LONG_TEXT[chunk.start_char:chunk.end_char] == chunk.content


def test_chunks_respect_max_size_and_are_never_empty():
    chunks = chunk_text(LONG_TEXT, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(0 < len(chunk.content) <= 200 for chunk in chunks)


def test_consecutive_chunks_overlap_and_cover_the_whole_text():
    chunks = chunk_text(LONG_TEXT, chunk_size=200, overlap=40)
    assert chunks[0].start_char == 0
    assert chunks[-1].end_char == len(LONG_TEXT.rstrip())
    for previous, current in zip(chunks, chunks[1:]):
        # Each chunk starts before the previous one ends: no gaps, some shared text.
        assert current.start_char < previous.end_char
        assert current.start_char > previous.start_char


def test_prefers_cutting_at_sentence_or_paragraph_ends():
    chunks = chunk_text(LONG_TEXT, chunk_size=200, overlap=40)
    assert all(chunk.content.endswith(".") for chunk in chunks[:-1])


def test_short_and_blank_text():
    assert [c.content for c in chunk_text("  Hello world.  ", 200, 40)] == ["Hello world."]
    assert chunk_text("   \n\n  ", 200, 40) == []


def test_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text(LONG_TEXT, chunk_size=100, overlap=100)
