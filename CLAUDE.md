# Ask Onboarding — notes for Claude Code

Take-home project: a RAG app that answers employee questions only from uploaded company documents, with citations and a help-desk ticket fallback. The deadline is 2 days, and the commit history is reviewed.

## Stack
- Backend: FastAPI (Python 3.12) in `backend/app`, Postgres + pgvector, fastembed (`bge-small-en-v1.5`, 384 dims), Anthropic Claude for answers.
- Frontend: React + TypeScript + Vite in `frontend/src`. All API calls go through `src/api/`.
- Run everything with `docker compose up --build`. Run tests with `docker compose run --rm backend pytest -v`.

## Rules
- Never put API keys in frontend code or in commits. Settings come from `app/config.py` (environment variables).
- The answer must come only from retrieved chunks. If no chunk passes `MIN_SIMILARITY`, do not call the LLM: return the no-answer event and offer a ticket.
- Every citation must carry `document_id`, `start_char` and `end_char` so the UI can highlight the exact passage.
- Re-uploading a file with the same name deletes its old chunks in the same transaction that inserts the new ones.
- Tests must never call the real LLM. Use the fakes in `tests/conftest.py`.
- Keep commits small, one feature each, with messages like `add pdf parser with page offsets`.
- Explain non-obvious code. I must be able to explain every line in the review call.
