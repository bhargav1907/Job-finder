# Progress — FLA Job Finder

> Single source of active state. Read at session start; update after each finished step.
> Keep under ~60 lines. History belongs in `git log`, not here.

## Current focus

- **Last done:** M1 — seed corpus, normalization, idempotent ingest, local embeddings,
  `GET /api/jobs`, local LLM client, `/api/health/llm` (commits `6874a0d`, `5be0233`,
  `f04582d`).
- **In progress:** none.
- **Next:** M2 — resume upload and parse.
- **Then:** M3 retrieval, M4 rerank + cache, M5 frontend, M6 tests/docs.

## Decisions & invariants

1. **Local models only.** `lfm3:1.7b`, fallback `llama3.2:3b` on invalid JSON. Never point
   `LLM_BASE_URL` at a hosted or coding-plan endpoint (16 GB machine; credential is
   licensed for harnesses only).
2. **Cache before tokens.** Every LLM call checks the `matches` table first.
3. **Validate batch output.** A rerank response is untrusted until every requested
   `job_id` is present; small local models silently drop items.
4. **Demo data only.** The app never fetches jobs at runtime; the UI carries the demo badge.
5. **Tavily is the only web path**, and it is budgeted at 1,000 requests/month.
6. **Top-level split by runtime:** `backend/` and `frontend/` (Vite app, source in
   `frontend/src/`). No root `src/` — the empty root `src/` scaffold was removed on
   2026-11-03.

## Open questions

- Resume upload formats and where parsed resumes are stored — ask Bhargav first.

## Maintenance

- Update "Current focus" and add new invariants after each finished step.
- Move completed milestone detail to the commit message and delete it here.
