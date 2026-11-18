"""Split text into overlapping chunks, keeping start/end character offsets for citations."""
from dataclasses import dataclass

# Where we prefer to cut a chunk, best first: paragraph, line, sentence, word.
BREAK_POINTS = ("\n\n", "\n", ". ", " ")


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_char: int  # text[start_char:end_char] == content, so the UI can highlight it exactly
    end_char: int


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[TextChunk]:
    """Cut `text` into pieces of at most `chunk_size` characters.

    Consecutive chunks share about `overlap` characters, so a sentence that
    falls on a boundary still appears whole in at least one chunk.
    """
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("chunk_size must be positive and 0 <= overlap < chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            end = _natural_break(text, start, end)

        piece = text[start:end]
        if piece.strip():
            # Trim surrounding whitespace but move the offsets with it.
            leading = len(piece) - len(piece.lstrip())
            trailing = len(piece) - len(piece.rstrip())
            chunks.append(TextChunk(piece.strip(), start + leading, end - trailing))

        if end == len(text):
            break
        # Step back by `overlap`, but always move forward at least one character.
        start = max(end - overlap, start + 1)
    return chunks


def _natural_break(text: str, start: int, end: int) -> int:
    """Move `end` back to the best break point in the second half of the window."""
    earliest = start + (end - start) // 2
    for separator in BREAK_POINTS:
        position = text.rfind(separator, earliest, end)
        if position != -1:
            return position + len(separator)
    return end  # one very long word: hard cut
