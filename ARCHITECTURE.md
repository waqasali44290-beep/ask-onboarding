# Architecture — Ask Onboarding

> Keep this to 1–3 pages. Fill in each _TODO_ once the decision has been tested.

## Diagram

```mermaid
flowchart LR
    U[Browser<br/>React app] -->|upload file| N[nginx]
    U -->|question| N
    N -->|/api| API[FastAPI backend]

    subgraph Ingestion
        API --> P[Parser<br/>PDF/MD/TXT] --> C[Chunker] --> E1[Embedder<br/>bge-small]
    end
    E1 --> DB[(Postgres + pgvector<br/>documents, chunks,<br/>messages, tickets)]

    subgraph Answering
        API --> E2[Embed question] --> R[Retriever<br/>top-k cosine] --> D{Relevant<br/>chunks?}
        D -- no --> NA[Not in documents<br/>+ offer ticket]
        D -- yes --> L[Claude LLM<br/>grounded prompt]
    end
    R <--> DB
    L -->|SSE tokens + citations| U
    NA -->|SSE| U
    U -->|Yes, create ticket| API --> DB
```

## 1. How it works today

The path of one question, step by step: _TODO_ (browser → nginx → `/api/chat` → embed → pgvector search → threshold check → prompt → Claude stream → SSE → UI renders citations).

## 2. Our choices

| Decision | Choice | Why / what was tried |
|---|---|---|
| Chunk size / overlap | 800 / 120 chars | _TODO: eval numbers vs 400/60_ |
| Embedding model | bge-small-en-v1.5 (local) | _TODO_ |
| Vector store | pgvector | One database; transactional replace-on-reupload |
| top-k | 5 | _TODO_ |
| No-answer detection | similarity threshold + prompt rule | _TODO_ |
| LLM | claude-sonnet-5-5 | _TODO_ |

What didn't work: _TODO_

## 3. Scaling up (5,000 employees, 200k docs, 20k questions/day)

- **Ingestion:** _TODO_ (job queue, incremental sync by hash/modified time, batched embeddings)
- **Storage:** _TODO_ (vector count, HNSW memory, partitioning, or a dedicated vector DB)
- **Latency:** _TODO_ (caching, smaller models, streaming)
- **Cost:** _TODO_ (tokens per question × 20k/day, prompt caching)

## 4. Failure modes (LLM provider down for 30 minutes)

_TODO: what the user sees (clear error, retrieved sources still shown), retries/backoff, recovery._

## 5. Quality: catching regressions before release

_TODO: run the eval set in CI, compare against a baseline, LLM-as-judge plus a human spot check._

## 6. RAG vs. fine-tuning

_TODO_
