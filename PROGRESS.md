# Progress — FLA Job Finder

> Single source of active state. Read at session start; update after each finished step.
> Keep under ~60 lines. History belongs in `git log`, not here.

## Current focus

- **Last done:** M5 — frontend. Placement-desk dossier: dark default + light, three panes
  ≥1280px, candidate strip at 768–1279, list↔detail below. URL carries `resume`/`job`.
  Verified: `npm --prefix frontend test` (39), `build`, `test:visual` (4, axe clean), and
  a real recommendations call → 200, 30 items, rerank unavailable without Ollama.
  Fresh whole-branch review: no Critical findings; one Important fix (retry on a failed
  candidate-file load).
- **In progress:** none.
- **Next:** M6 — SmartRecruiters + Freshteam adapters and an India-only board filter.
- **Then:** Postgres + pgvector migration.

## Decisions & invariants

1. **Local models only.** Parse uses `qwen3:4b` (~3.9 GB at 8K), rerank uses `lfm3:1.7b`,
   fallback `llama3.2:3b` on invalid JSON. `gemma4:12b` thrashed this 16 GB machine.
   Never point `LLM_BASE_URL` at a hosted or coding-plan endpoint.
2. **Salary is reconciled deterministically.** `parse_salary()` is authoritative for LPA;
   a monthly stipend is multiplied by 12; inverted ranges become null. Never trust the
   model's units.
3. **Cache before tokens.** Every LLM call checks the `matches` table first; resume
   dedupe by content hash happens before any parse call.
4. **Validate batch output.** A rerank response is untrusted until every requested
   `job_id` is present; small local models silently drop items.
5. **Demo data only.** The app never fetches jobs at runtime; the UI carries the demo badge.
6. **Tavily is the only web path**, and it is budgeted at 1,000 requests/month.
7. **Top-level split by runtime:** `backend/` and `frontend/` (source in `frontend/src/`).
   No root `src/`.
8. **Retrieval is deterministic and LLM-free.** Explicit hard filters only, score =
   `0.85 × cosine + 0.15 × skill share`, up to 40 candidates per bucket. No filter is
   inferred from the resume.
9. **A salary floor never hides unstated salaries.** Same-currency jobs below the floor
   are excluded; missing or non-comparable salaries return in `items_without_salary`.
10. **M4 returns up to 30 results.** Target 20 salary-known + 10 salary-unstated,
    backfilling unused slots from the other list. Scores blend 0.7 × LLM fit with
    0.3 × retrieval.
11. **Rerank cache keys include the model.** `prompt_version` is
    `rerank-v1@<llm_rerank_model>`; change it with the model or prompt. SQLite BLOBs and
    in-memory numpy are enough until the Postgres + pgvector migration.
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
17. **Dark is the default; light is opt-in.** `fla.theme` is applied before paint and
    persists. The demo badge stays visible at every width.
18. **The UI reports only what the API returned.** Missing pay says "Pay not stated";
    `remote: false` is never relabelled; retrieval-only results say so. Scores are 0–100
    and INR pay is displayed as LPA.

## Open questions

- None.
