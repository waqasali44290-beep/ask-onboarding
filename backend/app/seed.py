"""Load every PDF/MD/TXT file from a folder: docker compose exec backend python -m app.seed

Files inside a folder named "managers" are marked managers-only."""
import sys
from pathlib import Path

from app.db import SessionLocal
from app.ingestion.parsers import MIME_TYPES
from app.ingestion.pipeline import ingest_document, register_upload
from app.ingestion.suggestions import generate_quiz, suggest_questions


def seed(folder: Path, force: bool = False) -> None:
    """force=True re-indexes unchanged files too, e.g. after changing CHUNK_SIZE."""
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in MIME_TYPES or path.name == "README.md":  # README describes the folder
            continue
        data = path.read_bytes()
        with SessionLocal() as session:
            visibility = "managers" if "managers" in path.relative_to(folder).parts else "everyone"
            document, needs_ingestion = register_upload(session, path.name, data, visibility)
        if needs_ingestion or force:
            ingest_document(document.id, path.name, data)
        if needs_ingestion or force or not document.suggested_questions:
            suggest_questions(document.id)  # one LLM call per document, ~20 s on CPU
        if needs_ingestion or force or not document.quiz:
            generate_quiz(document.id)
        print(f"{path.relative_to(folder)}: {'indexed' if needs_ingestion or force else 'unchanged'}")


if __name__ == "__main__":
    arguments = [a for a in sys.argv[1:] if a != "--force"]
    seed(Path(arguments[0] if arguments else "/sample-docs"), force="--force" in sys.argv)
