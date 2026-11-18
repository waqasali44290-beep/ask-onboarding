"""Load every PDF/MD/TXT file from a folder: docker compose exec backend python -m app.seed"""
import sys
from pathlib import Path

from app.db import SessionLocal
from app.ingestion.parsers import MIME_TYPES
from app.ingestion.pipeline import ingest_document, register_upload


def seed(folder: Path) -> None:
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in MIME_TYPES or path.name == "README.md":  # README describes the folder
            continue
        data = path.read_bytes()
        with SessionLocal() as session:
            document, needs_ingestion = register_upload(session, path.name, data)
        if needs_ingestion:
            ingest_document(document.id, path.name, data)
        print(f"{path.relative_to(folder)}: {'indexed' if needs_ingestion else 'unchanged'}")


if __name__ == "__main__":
    seed(Path(sys.argv[1] if len(sys.argv) > 1 else "/sample-docs"))
