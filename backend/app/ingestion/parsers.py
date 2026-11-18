"""Turn an uploaded PDF / Markdown / TXT file into plain text (+ page offsets for PDFs)."""
import io
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}

# Pages are joined with a blank line so a chunk never glues two pages' words together.
PAGE_SEPARATOR = "\n\n"


class ParseError(ValueError):
    """The file can't be turned into text. The message is shown to the user."""


@dataclass
class ParsedDocument:
    text: str
    # Character offset where each PDF page starts in `text`; empty for md/txt.
    page_starts: list[int] = field(default_factory=list)

    def page_for_offset(self, offset: int) -> int | None:
        """1-based page number containing `offset`, or None for non-PDF files."""
        if not self.page_starts:
            return None
        return bisect_right(self.page_starts, offset)


def mime_type_for(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in MIME_TYPES:
        raise ParseError(f"Unsupported file type '{extension}'. Upload a PDF, Markdown or TXT file.")
    return MIME_TYPES[extension]


def parse_file(filename: str, data: bytes) -> ParsedDocument:
    if mime_type_for(filename) == "application/pdf":
        parsed = _parse_pdf(data)
    else:
        # errors="replace": a stray non-UTF-8 byte becomes "�" instead of failing the upload.
        # Normalising Windows line endings keeps character offsets consistent.
        parsed = ParsedDocument(text=data.decode("utf-8", errors="replace").replace("\r\n", "\n"))

    if not parsed.text.strip():
        raise ParseError("The file contains no readable text (scanned PDFs are not supported).")
    return parsed


def _parse_pdf(data: bytes) -> ParsedDocument:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises many different error types for broken files
        raise ParseError(f"Could not read the PDF: {exc}") from exc

    page_starts = []
    offset = 0
    for page_text in pages:
        page_starts.append(offset)
        offset += len(page_text) + len(PAGE_SEPARATOR)
    return ParsedDocument(text=PAGE_SEPARATOR.join(pages), page_starts=page_starts)
