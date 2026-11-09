# Progress — FLA Job Finder

> Single source of active state. Read at session start; update after each finished step.
> Keep under ~60 lines. History belongs in `git log`, not here.

## Current focus

- **Last done:** M4.5 — live India ATS sources. `data/boards.json` lists 18 validated
  boards; Greenhouse, Keka, and Darwinbox adapters sit behind `JobSource`. A live
  smoke ingest fetched 3,627 postings (Darwinbox 2,855, Greenhouse 674, Keka 98) and
  a second run inserted 0. Research: `docs/research/india-ats-probe-2026-11-09.md`.
- **In progress:** none.
- **Next:** M5 — frontend.
- **Then:** SmartRecruiters + Freshteam adapters and an India-only board filter.

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
8. **Retrieval is deterministic and LLM-free.** Explicit hard filters only, score =
   `0.85 × cosine + 0.15 × skill share`, up to 40 candidates per bucket. No filter is
   inferred from the resume.
9. **A salary floor never hides unstated salaries.** Same-currency jobs below the floor
   are excluded; missing or non-comparable salaries return in `items_without_salary`.
10. **M4 returns up to 30 results.** Target 20 salary-known + 10 salary-unstated,
    backfilling unused slots from the other list. Scores blend 0.7 × LLM fit with
    0.3 × retrieval.
11. **Rerank cache keys include the model.** `prompt_version` is
    `rerank-v1@<llm_rerank_model>`; changing the model or prompt must change the string.
    A vector store waits for the Postgres + pgvector migration; SQLite BLOBs and
    in-memory numpy are enough for the demo corpus.
12. **`data/boards.json` is the only live board list.** Adapters never invent a host;
    Darwinbox boards must match `<tenant>.darwinbox.(in|com)`.
13. **Live ingest is CLI-only** (`python -m app.cli ingest --live`). API requests never fetch.
14. **Jobs are identified by `(source, external_id)`**; adapters namespace the provider's
    id with the board (`softobiz:7`) because ATS ids repeat across tenants. Fingerprint
    dedupes the same job across sources and covers rows with no external id.
15. **No posting lifecycle yet.** `last_seen_at` / `closed_at` need a schema change, so a
    vanished live posting stays in the DB until that is approved.
16. **Live salaries stay unstated.** Adapters do not guess currency or period; structured
    pay parsing is deferred.

## Open questions

- None.

## Maintenance

- Update "Current focus" and add new invariants after each finished step.
- Move completed milestone detail to the commit message and delete it here.
