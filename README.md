# Ask Onboarding — AI Knowledge Assistant

A full-stack app where new employees upload company documents (handbook, engineering wiki, IT guides) and ask questions in plain language. The assistant:

- answers **only** from the uploaded documents,
- shows **clickable citations** that open the exact source passage,
- says plainly **"I couldn't find this in the documents"** instead of guessing,
- and then offers to **open a help-desk ticket** for the question.


---

## Features

### Core requirements

| # | Requirement | Where it lives |
|---|---|---|
| F1 | Upload PDF / Markdown / TXT, list documents with status (processing, ready, failed) | `frontend/src/pages/UploadPage.tsx`, `backend/app/api/documents.py` |
| F2 | Chat page with streaming answers and visible conversation history | `frontend/src/pages/ChatPage.tsx`, `backend/app/api/chat.py` |
| F3 | Clickable citations that open the source document at the exact passage | `frontend/src/components/CitationPanel.tsx`, `chunks.start_char/end_char` |
| F4 | Clear empty, loading and error states | `frontend/src/components/States.tsx` |
| B1 | Ingestion: parse → chunk → embed → store in pgvector | `backend/app/ingestion/` |
| B2 | Retrieval endpoint returning top matching chunks | `POST /api/retrieve` |
| B3 | Answer endpoint: retrieved chunks → LLM → streamed answer | `POST /api/chat`, `backend/app/rag/` |
| B4 | Honest "not in the documents" answer | `backend/app/rag/answerer.py` (similarity threshold + prompt rule) |
| B5 | Tool call: offer a help-desk ticket, save it, show it on `/tickets` | `backend/app/api/tickets.py`, `TicketsPage.tsx` |
| B6 | Re-uploading a changed file replaces its old chunks | `backend/app/ingestion/pipeline.py` |

### Stretch goals

1. **Evaluation**: 20 test questions with expected answers, plus a script that scores retrieval hit rate and answer quality. Used to compare chunk sizes 400 and 800. Results are reported [below](#evaluation-results).
2. **Prompt-injection defence**: a sample document contains hidden "ignore previous rules…" text, and the app does not follow it.
3. **Access control**: documents can be marked *managers only* (admins choose on upload or per document; the seed command marks `sample-docs/managers/`). The filter is part of the retrieval query, so an employee's question can never bring that text to the LLM, however it is phrased. `tests/test_access_control.py` proves it with direct, sneaky and "ignore your rules" questions, and checks that the hidden text never appears in any prompt sent to the model.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Fast dev server, typed API contract |
| Backend | Python 3.12 + FastAPI | Async, built-in streaming responses, auto API docs at `/docs` |
| Vector store | PostgreSQL 16 + **pgvector** | One database for documents, chunks, chats and tickets |
| Embeddings | `BAAI/bge-small-en-v1.5` via **fastembed** (runs locally) | No extra API key, fast on CPU, 384 dimensions |
| LLM | **Ollama** running `qwen2.5:3b` locally | Free, no API key, data never leaves the machine; small enough for a CPU-only laptop |
| PDF parsing | pypdf | Pure Python, keeps page numbers |
| Streaming | Server-Sent Events | One-way token stream; simple to proxy through nginx |
| Run | Docker Compose | `docker compose up` starts db, backend and frontend |
| Tests | pytest | Chunking, retrieval, no-answer, re-upload, tickets |

---

## Project structure

```
.
├── README.md                 # You are here
├── ARCHITECTURE.md           # System diagram + design decisions (required)
├── AI_LOG.md                 # AI tools, key prompts, AI mistakes caught (required)
├── CLAUDE.md                 # Context for Claude Code while developing
├── docker-compose.yml        # db + ollama + backend + frontend
├── .env.example              # Copy to .env; all settings in one place
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── db/init.sql           # Schema: documents, chunks (vector), conversations, messages, tickets
│   ├── app/
│   │   ├── main.py           # FastAPI app + router registration
│   │   ├── config.py         # Settings from environment variables
│   │   ├── db.py             # DB engine / session
│   │   ├── models.py         # ORM models
│   │   ├── schemas.py        # Request/response models (the API contract)
│   │   ├── api/              # HTTP routes
│   │   │   ├── documents.py  #   upload, list, get, delete
│   │   │   ├── retrieval.py  #   POST /api/retrieve
│   │   │   ├── chat.py       #   POST /api/chat (SSE stream)
│   │   │   └── tickets.py    #   create / list tickets
│   │   ├── ingestion/        # File → chunks → vectors
│   │   │   ├── parsers.py    #   PDF / MD / TXT → text
│   │   │   ├── chunker.py    #   overlapping chunks with char offsets
│   │   │   └── pipeline.py   #   orchestration + replace-on-reupload
│   │   └── rag/              # Question → answer
│   │       ├── embeddings.py #   local embedding model
│   │       ├── retriever.py  #   pgvector top-k search
│   │       ├── prompts.py    #   system prompt + context formatting
│   │       ├── llm.py        #   Ollama streaming client
│   │       └── answerer.py   #   retrieve → decide → stream
│   └── tests/                # pytest (≥5 tests, no real API calls)
│
├── frontend/
│   ├── Dockerfile            # build with Node, serve with nginx
│   ├── nginx.conf            # proxies /api to backend, streaming enabled
│   ├── package.json
│   └── src/
│       ├── App.tsx           # routes: /chat, /upload, /tickets
│       ├── types.ts          # shared types
│       ├── api/              # fetch wrappers + SSE stream reader
│       ├── hooks/            # useChat, useDocuments
│       ├── pages/            # ChatPage, UploadPage, TicketsPage
│       └── components/       # dropzone, document list, messages, citation panel, states
│
├── sample-docs/              # 15–30 sample company docs (≥1 PDF)
├── eval/                     # questions.jsonl + run_eval.py + results/
└── docs/screenshots/         # images used in this README
```

---

## Getting started

### Prerequisites

- Docker Desktop (with Docker Compose v2), with at least 8 GB of memory available to Docker
- About 4 GB of free disk for the images and models

No API keys are needed: the LLM and the embedding model both run locally.

### Run the app

```bash
git clone <repo-url> ask-onboarding
cd ask-onboarding
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| Web app | http://localhost:5173 |
| API + Swagger docs | http://localhost:8000/docs |
| Postgres | localhost:5432 (user/pass from `.env`) |
| Ollama | http://localhost:11434 |

The first start downloads the LLM (`qwen2.5:3b`, about 1.9 GB) and the embedding model (about 130 MB). Both are cached in Docker volumes, so later starts are fast.

### Demo accounts

| Username | Password | Can do |
|---|---|---|
| `employee` | `onboarding` | Chat, open tickets, see own tickets |
| `manager` | `onboarding` | Same as employee |
| `admin` | `onboarding` | Everything, plus manage documents and all tickets |

They are created on first start. Set `DEMO_PASSWORD` in `.env` to change the password.

### Load the sample documents

```bash
docker compose exec backend python -m app.seed
```

This loads the 18 documents in `sample-docs/`. You can also drag files into the **Documents** page.

### Local development (without Docker for the app code)

```bash
docker compose up db                      # only the database

# backend
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg://ask:ask@localhost:5432/ask_onboarding
uvicorn app.main:app --reload

# frontend (new terminal)
cd frontend
npm install
npm run dev                               # http://localhost:5173, proxies /api to :8000
```

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/documents` | Upload a file (multipart). Same filename replaces the old version |
| GET | `/api/documents` | List documents with status |
| GET | `/api/documents/{id}` | One document with full text (for the citation viewer) |
| DELETE | `/api/documents/{id}` | Delete a document and its chunks |
| POST | `/api/retrieve` | `{question, top_k?}` → top matching chunks + scores |
| POST | `/api/chat` | `{question, conversation_id?}` → SSE stream: `token`, `citations`, `no_answer`, `done`, `error` |
| GET | `/api/conversations/{id}` | Conversation history |
| POST | `/api/tickets` | `{title, question, user_name, conversation_id?}` |
| GET | `/api/tickets` | List tickets |

---

## Testing

```bash
docker compose run --rm backend pytest -v
```

| Test file | Covers |
|---|---|
| `test_parsers.py` | PDF/MD/TXT parsing, PDF page numbers, unsupported/empty/broken files |
| `test_chunking.py` | Chunk size/overlap, offsets map back to source text |
| `test_documents_api.py` | Upload → processing → ready, 400 for bad types, 404, delete |
| `test_retrieval.py` | Known question → correct chunk ranks first; top-k cap |
| `test_no_answer.py` | Off-topic question → "not in the documents" + ticket offer, no guessing |
| `test_reupload.py` | Changed file replaces old chunks |
| `test_tickets.py` | Ticket is saved and listed |

Tests use a fake LLM and a fake embedder, so they run in seconds and don't need Ollama.

---

## Evaluation results

20 questions in `eval/questions.jsonl`: 17 answerable (one from the PDF, one from the document with a hidden prompt injection) and 3 the documents don't cover.

```bash
docker compose exec backend python -m app.seed                       # load sample docs
docker compose exec backend python /eval/run_eval.py --label mytest   # ~5 min on CPU
```

| Config | Retrieval hit rate | Answer accuracy | Correct "no answer" | Injection resisted | Median time |
|---|---|---|---|---|---|
| **chunk 800 / overlap 120, top-k 5** (default) | 100% | **82%** (14/17) | 100% (3/3) | yes | 16.5 s |
| chunk 400 / overlap 60, top-k 5 | 100% | – (retrieval only) | – | – | – |
| chunk 800, top-k 3 + softer "not found" rule | 100% | 65% (11/17) | 100% (3/3) | yes | 8.8 s |

- **Chunk size made no difference** here: the sample documents are short (300–600 characters), so most fit in one chunk either way.
- **Fewer sources made the small model worse**, not better: it dropped citations and answered one question with only "[1]". So top-k stays 5.
- **Remaining failures** with the default: twice the model said "not found" although the right source was retrieved (doctor's note, Friday deploys), and once it cited the wrong source number. These are limits of a 3B model; a larger model would likely fix them.

Scoring is keyword-based and transparent: an answer counts as correct only if it contains the expected facts **and** cites the expected file.

## Screenshots

_TODO: add images to `docs/screenshots/` (upload page, chat with citations, no-answer + ticket, tickets page)._

---

## Known limitations

- No authentication: the ticket "user" is a name typed into the UI.
- Ingestion runs as a FastAPI background task, not a durable job queue, so a crash during ingestion leaves the document marked `failed`.
- Scanned PDFs (images only) are not OCR'd.
- The local LLM runs on CPU: expect about 10–20 seconds per answer, and about 40 seconds for the first question after start-up while the model loads into memory.
- Follow-ups use only the previous question and answer, not the whole conversation.

---

## Submission checklist

- [ ] Working source code, starts with `docker compose up`
- [ ] README.md: setup steps, screenshots, known limitations
- [ ] ARCHITECTURE.md with diagram
- [ ] AI_LOG.md
- [ ] ≥5 automated tests passing
- [ ] Small, meaningful commit history
- [ ] Demo video (≤5 minutes): _link here_
