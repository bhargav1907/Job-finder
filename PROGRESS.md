# Progress — FLA Job Finder

> Single source of active state. Read at session start; update after each finished step.
> Keep under ~60 lines. History belongs in `git log`, not here.

## Current focus

- **Last done:** M2 — resume upload and parse. PDF/DOCX/TXT upload, text extraction,
  schema-constrained ATS-profile parse with retry/fallback/heuristic, SHA-256 dedupe,
  SQLite storage, `POST /api/resumes`, `GET /api/resumes/{id}` (commits `b22f098`,
  `3afb6c7`).
- **In progress:** none.
- **Next:** M3 — retrieval.
- **Then:** M4 rerank + cache, M5 frontend, M6 tests/docs.

## Decisions & invariants

1. **Local models only.** Resume parse uses `qwen3:4b` (~3.9 GB loaded at 8K context);
   rerank uses `lfm3:1.7b`; fallback `llama3.2:3b` on invalid JSON. `gemma4:12b` is
   rejected on this machine — its 7.7 GB footprint thrashed 16 GB. Never point
   `LLM_BASE_URL` at a hosted or coding-plan endpoint.
2. **Salary is reconciled deterministically.** `parse_salary()` is authoritative for LPA;
   a monthly stipend is multiplied by 12; inverted ranges become null. Never trust the
   model's units.
3. **Cache before tokens.** Every LLM call checks the `matches` table first; resume
   dedupe by content hash happens before any parse call.
4. **Validate batch output.** A rerank response is untrusted until every requested
   `job_id` is present; small local models silently drop items.
5. **Demo data only.** The app never fetches jobs at runtime; the UI carries the demo badge.
6. **Tavily is the only web path**, and it is budgeted at 1,000 requests/month.
7. **Top-level split by runtime:** `backend/` and `frontend/` (Vite app, source in
   `frontend/src/`). No root `src/` — the empty root `src/` scaffold was removed on
   2026-11-03.

## Open questions

- None.

## Maintenance

- Update "Current focus" and add new invariants after each finished step.
- Move completed milestone detail to the commit message and delete it here.
