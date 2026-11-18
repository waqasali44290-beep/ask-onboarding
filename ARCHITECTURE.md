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
        D -- yes --> L[Ollama qwen2.5:3b<br/>grounded prompt]
    end
    R <--> DB
    L -->|SSE tokens + citations| U
    NA -->|SSE| U
    U -->|Yes, create ticket| API --> DB
```

## 1. How it works today

1. **Browser** (React, `ChatPage`): the user sends a question; `stream.ts` POSTs it to `/api/chat` and starts reading the response as a stream.
2. **nginx** (frontend container) forwards `/api/*` to the backend with buffering off, so streamed tokens pass straight through.
3. **FastAPI** (`api/chat.py`) validates the request and hands it to `rag/answerer.py`, which saves the question to the `messages` table.
4. **Embedding** (`rag/embeddings.py`): the question is turned into a 384-number vector by bge-small, running inside the backend process.
5. **Retrieval** (`rag/retriever.py`): pgvector returns the 5 chunks with the highest cosine similarity, only from documents whose status is `ready`.
6. **Cutoff:** chunks under 0.50 similarity are dropped. If none are left, the answerer streams the no-answer message and ticket offer, without calling the LLM.
7. **Prompt** (`rag/prompts.py`): the system prompt (rules: sources only, cite `[n]`, reply `NOT_FOUND` if not covered, ignore instructions inside sources) plus the numbered sources in `<source>` tags and the question.
8. **LLM** (`rag/llm.py`): Ollama runs qwen2.5:3b at temperature 0 and streams tokens back.
9. **Back to the browser:** the answerer sends Server-Sent Events: `sources`, then `token` events (held back until they can't be the `NOT_FOUND` marker), then `done` with only the sources the answer cited. The answer is saved with its citations.
10. **UI:** tokens appear as they arrive; `[n]` markers become buttons that open the document with the exact passage highlighted, using the chunk's `start_char`/`end_char`.

## 2. Our choices

| Decision | Choice | Why / what was tried |
|---|---|---|
| Chunk size / overlap | 800 / 120 chars | Same 100% retrieval hit rate as 400/60 on the eval set (documents are short); 800 keeps whole policies together |
| Embedding model | bge-small-en-v1.5 (local, fastembed) | Free, no API key, ~130 MB, fast on CPU; 100% retrieval hit rate on the eval set. Its scores are compressed (unrelated text still ~0.4–0.6), which shaped the cutoff choice below |
| Vector store | pgvector | One database; transactional replace-on-reupload |
| top-k | 5 | top-k 3 was 2× faster but answer accuracy fell from 82% to 65% (see README) |
| No-answer detection | similarity cutoff 0.50 + prompt rule | Two layers, because a cutoff alone can't do it (see below) |
| LLM | qwen2.5:3b via Ollama | Free and local (training project, no API budget). 3B is the largest that answers at a usable speed on a CPU-only laptop with 8 GB for Docker. See the first live test below. |

**Choosing the no-answer cutoff.** I scored 16 questions against 6 short policy documents (bge-small, best-chunk cosine similarity):

| Question type | Score range | Examples |
|---|---|---|
| Answerable | 0.65 – 0.85 | "How many vacation days do I get?" 0.71, "What do I do if my laptop is stolen?" 0.85 |
| General knowledge | ~0.37 | "What is the capital of France?" 0.37 |
| Sounds like company policy, not covered | 0.49 – 0.62 | "Parental leave policy?" 0.62, "Wifi password?" 0.59, "Dress code?" 0.49 |

The third group overlaps the first ("parental leave" 0.62 vs "carry over unused leave" 0.65), so no single cutoff separates them. The cutoff (0.50) therefore only removes clearly off-topic questions, which get an instant "not in the documents" without an LLM call. Near-misses reach the LLM, and the prompt makes it say when the sources don't cover the question. I chose 0.50 rather than 0.55 because real chunks are longer than these test passages, and longer chunks score lower. On the 20-question eval set this gives 100% correct no-answers with no answerable question blocked by the cutoff.

**First live test of the LLM** (qwen2.5:3b, CPU only, i7-1355U, 6 short documents):

| Question | Result | Time |
|---|---|---|
| What should I do if my laptop is stolen? | Correct and complete; cited only the right source | 49 s (includes loading the model) |
| Can I use Jira from home, and how many vacation days do I get? | Combined two documents; cited both correctly | 13 s to first token, 21 s total |
| What is the company's parental leave policy? | Model replied NOT_FOUND from 4 related sources → no-answer + ticket offer | 9 s |
| What is the capital of France? | Below the cutoff → no-answer without an LLM call | 0.1 s |

Most of the wait is the CPU reading the prompt (5 sources × up to 800 characters) before the first token. A GPU or a hosted LLM API would cut it to about 1 s. Lowering top-k also halves it, but hurt accuracy (below).

What didn't work:
- The original default cutoff of 0.35 let every question through, because bge-small scores even unrelated text around 0.35–0.6.
- Top-k 3 plus a softer "not found" rule, meant to fix two false "not found" answers: accuracy fell from 82% to 65%. The 3B model dropped citations with fewer sources. Reverted.
- Chunk size 400 vs 800 made no measurable difference, because the sample documents are short.

## 3. Scaling up (5,000 employees, 200k docs, 20k questions/day)

**What breaks first: the LLM.** 20,000 questions a day is about 0.25 per second on average, and maybe 1–2 per second at peak. One CPU Ollama answers one question in about 16 s, so the queue grows within minutes.

- **LLM / latency:** serve the model on GPUs with a batching server (e.g. vLLM), or use a hosted LLM API. Either gives about 1 s to first token. Cache answers to repeated questions (onboarding questions repeat a lot), keyed by question embedding plus document versions.
- **Ingestion:** today ingestion runs as an in-process background task. Instead:
  - Move it to a job queue with separate workers, so uploads and nightly syncs never slow down chat.
  - Use the Google Drive and Confluence change APIs to process only changed and deleted documents each night, plus a weekly full reconcile.
  - The existing content hash already skips unchanged files.
  - Batch embeddings, or use a GPU for them. A full re-embed of about 2M chunks takes hours on CPU, but an incremental nightly sync is a few percent of that.
- **Storage:** 200k documents is about 2M chunks × 384 floats ≈ 3 GB of vectors, plus the HNSW index. That still fits pgvector on one larger Postgres instance with read replicas. Options if it grows:
  - store vectors as half precision (`halfvec`) to halve memory;
  - partition by source;
  - move vectors to a dedicated store (Qdrant) while metadata stays in Postgres.
- **Access control:** with real Confluence and Drive data, permissions matter. Store each document's allowed groups on its chunks and filter in the retrieval query, never only in the UI.
- **Cost:** self-hosted means paying for GPU hours, not tokens. With a hosted API, a question is roughly 1,500 input + 200 output tokens. At an illustrative $1 per million input and $5 per million output tokens, that's about $30 + $20 per day for 20k questions. Answer caching and the similarity cutoff, which skips the LLM for off-topic questions, both reduce this.

## 4. Failure modes (LLM down for 30 minutes)

**What the user sees today:**
- Retrieval still works, since it doesn't use the LLM.
- When the LLM can't be reached, the stream sends an `error` event. The chat shows "The assistant is unavailable right now. Please try again in a few minutes." with a **Try again** button, instead of a blank page or a spinner that never ends.
- Questions below the cutoff still get the no-answer reply and the ticket offer, because they never reach the LLM.
- Uploads keep working, since ingestion only needs the embedding model.

**Recovery:** there is nothing to repair. Each request is independent, the question is already saved, and the next request after the LLM is back works normally.

**What I would add:**
- `restart: unless-stopped` and a health check on the LLM service.
- A short retry with backoff for brief outages.
- A circuit breaker, so that during a long outage the app fails fast instead of waiting for timeouts.
- An outage fallback that shows the top retrieved passages with their citations ("Here are the most relevant passages"). That's still useful without generation.
- A secondary model or provider.

## 5. Quality: catching regressions before release

- **Eval set in CI:** run `eval/run_eval.py` on every change to prompts, models, chunking or retrieval. Block the release if answer accuracy, citation accuracy or no-answer accuracy drops below the current baseline (today 82% / 100%). The top-k experiment above is exactly the kind of regression this catches.
- **Grow the eval set:** from 20 to a few hundred questions, using real employee questions from chat logs and tickets. Include near-miss "not covered" questions and injection attempts.
- **Better scoring than keywords:** add an LLM-as-judge for faithfulness ("is every claim supported by the cited source?") and relevance, calibrated against a small human-graded sample. Spot-check a sample of changed answers by hand before each release.
- **After release:** compare the new version against the old on live traffic, with thumbs up/down and ticket rate as signals, and keep the old prompt or model ready to roll back.

## 6. RAG vs. fine-tuning

RAG stays the core. The facts change nightly, every answer needs a citation, and access control has to apply per document. Fine-tuning can't do any of that: a fine-tuned model can't cite or "forget" an outdated policy.

Fine-tuning becomes worth it **in addition to RAG** when:
- **The model's behaviour is the problem, not its knowledge.** That is exactly what the eval shows for the 3B model: false "not found" answers and wrong citation numbers. Fine-tuning a small model on a few thousand (question, sources, ideal cited answer / NOT_FOUND) examples would teach the format and grounding rules. It would let a cheap, fast local model match a larger one.
- **Retrieval misses company jargon** (product code names, team acronyms). Fine-tuning the embedding model on question→document pairs from logs improves recall.
- **Cost or latency at scale:** distilling a large model's grounded answers into a smaller model lowers the cost per question.
