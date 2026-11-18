# AI Log

## Tools used

| Tool | Used for |
|---|---|
| Claude Code (VS Code extension, Claude Opus 5.5) | Reading the brief, project structure, backend, frontend, tests, Docker setup, evaluation, docs |

Workflow: one feature per branch. The AI wrote the code and tests; every feature was then run against the real app (curl, the live model, the eval script) before merging. Most bugs below were found that way, not by the unit tests.

## Key prompts

1. **"Read all requirements and functionality; I need organisation structure, file architecture and a README, and which tools to install."** Produced the folder layout, docker-compose, the DB schema and the README skeleton. I chose FastAPI + React + pgvector here.
2. **"Run it yourself" / "Install Docker for me."** The AI found that WSL was missing and installed it. A restart was needed, which it correctly left to me.
3. **"Do all 3 steps": git init, then the ingestion feature.** Ingestion came as 5 small commits, each with tests.
4. **"Push the repo to my GitHub."** Created a private repo and pushed.
5. **"Continue" with retrieval.** I asked for the no-answer cutoff to be measured rather than guessed. The probe of 16 questions became the threshold decision in ARCHITECTURE.md.
6. **"I'm in training, I'd like to use Ollama."** Switched from a paid API to a local qwen2.5:3b, with automatic model download in docker compose.
7. **Frontend:** upload, chat with streaming and citations, tickets, and empty/loading/error states.
8. **Evaluation:** 20 questions, a scoring script, and a chunk-size comparison.
9. **"Please use minimum tokens."** Asked the AI to keep replies and checks short.

## Where the AI was wrong and how it was caught

| What the AI did | How it was caught | Fix |
|---|---|---|
| Set the no-answer cutoff (`MIN_SIMILARITY`) to 0.35 by guess | Measured real scores: unrelated questions score 0.35–0.6 with bge-small, so nothing was ever rejected | Raised to 0.50 and documented the measurements |
| Uploading the same file twice while the first was still processing started two ingestions | End-to-end upload with curl returned 202 the second time | Skip identical content unless the previous attempt failed; added a test |
| nginx cached the backend's IP, so every backend restart caused 502 errors | Live test after rebuilding the backend | Re-resolve through Docker DNS (`resolver` + variable in `proxy_pass`) |
| fastembed cached the model in `/tmp`, so it would re-download on every container recreate | Inspected the library's default cache path | Pointed the cache at the mounted volume |
| The seed script indexed `sample-docs/README.md` as a company document | Seed output listed it | Skip README files |
| A test assumed a document would pass the cutoff with the fake embedder | The test failed | Lowered the cutoff inside that test so it tests what it claims |
| A prompt change plus top-k 3, meant to fix two wrong "not found" answers, dropped accuracy from 82% to 65% | The eval script | Reverted; kept as a documented "didn't work" |
| Assumed Docker Desktop was in `C:\Program Files` | Start-Process error | Located it and found the real blocker (WSL) |
| Frontend: put a `<div>` inside an `<ol>`, and used `Array.at()`, which the TypeScript target doesn't include | Code review / type check | Moved the div; used index access |

## Written or fixed by hand

_To fill in yourself before submitting: which parts you changed by hand, what you reviewed line by line, and anything you rewrote after the AI's version. The reviewers will ask you to explain any line, so go through each file and note what you would explain differently._
