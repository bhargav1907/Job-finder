# M3 — Retrieval: design

Date: 2026-11-06
Status: approved

## Intent

Turn a stored resume into ~40 ranked candidate jobs, cheaply and deterministically, so
M4 can spend LLM tokens only on those candidates. This is the recall stage: if a good
job is missing here, M4 can never recover it.

Success: a student's resume plus optional filters returns the sensible jobs in the top
20, in milliseconds, with no model call and no network access.

## Goals

- Filter jobs by location, remote, experience, role, and salary when the student asks.
- Rank the remaining jobs by local embedding similarity, with a small exact-skill boost.
- Return up to 40 candidates and enough metadata for M4 and the frontend.
- Keep jobs with missing salary visible in a separate bucket instead of dropping them.
- Include experience highlights and certifications in the resume embedding.
- Expose the candidate list over HTTP for M4 and the frontend.

## Non-goals

- LLM reranking, fit scores, reasons, gaps, and caching (M4).
- The frontend UI (M5).
- Pagination, offsets, or result diversification.
- Currency conversion.
- A vector database or approximate nearest-neighbour index.
- Database schema changes.
- Treating cosine similarity as a fit score.

## Anti-goals

- Silently dropping jobs that lack salary data when a salary filter is set.
- Silently relaxing or ignoring an explicit filter.
- Applying resume preferences as hidden server-side filters.
- Returning a semantic score that the UI presents as a fit score.
- Adding a dependency or a second service for a 100-job demo corpus.

## Constraints

- Python 3.14, FastAPI, SQLModel, SQLite. No schema change; embeddings stay as SQLite
  BLOBs and are scanned in memory with numpy.
- No new dependency. `numpy`, `fastembed`, and the BGE-small model are already present.
- No LLM call in M3. Retrieval must work offline and without Ollama.
- The embedding model is `BAAI/bge-small-en-v1.5` (384 dimensions, L2-normalized).
- The app is a demo: 100 seed jobs, no auth, no live feeds.
- Hard filters apply only when explicitly supplied in the request. The server never
  applies the resume's own preferences as filters.
- `top_k` candidate default is 40; M4 returns up to 30 final results, targeting 20
  salary-known + 10 salary-unstated and backfilling unused slots from the other list.

## Approaches considered

1. **Explicit hard filters + in-memory cosine + small skill boost (chosen).**
   Filter in SQL, score the filtered rows in numpy, sort. Predictable, no infrastructure,
   and fast at the demo's scale. Filters only exclude when the student asks, so the
   default search is pure semantic ranking.
2. **Soft filters with weighted preference scores.** Rank all jobs and let location or
   salary preferences nudge the order. Better for near-misses, but it hides the meaning
   of a filter and makes "why is this job here?" harder to answer. Rejected for v1;
   M4 can consider fit nuance with the LLM.
3. **Vector database (pgvector, sqlite-vec, Chroma).** Better for tens of thousands of
   jobs, but adds a dependency or a service and still needs SQL filters. Deferred;
   Postgres + pgvector is the documented migration path when the corpus grows.

## Design

### Public API

`GET /api/resumes/{resume_id}/recommendations`

Read-only. Query parameters, all optional:

- `location: str` — case-insensitive substring on the job location; the term `remote`
  also matches jobs flagged `remote = true`.
- `remote: bool` — exact match.
- `experience_years: int` (0–60) — maps to two adjacent seniority tiers: 0 → intern and
  junior; 1–2 → junior and mid; 3–5 → mid and senior; 6+ → senior and lead.
- `role: str` — mapped through `infer_role_family`; when the family is `other`, falls
  back to a title substring.
- `salary_min: int` (annual, in the resume's currency) — keeps jobs whose `salary_max`
  is at least this value.
- `limit: int` — default `settings.top_k` (40), between 1 and 100.

All filters are ANDed. No filter is applied when its parameter is absent.

Responses:

- `200 RecommendationList`.
- `404` when the resume does not exist.
- `422` for invalid query values (negative years/salary, limit outside 1–100).

`RecommendationList`:

- `resume_id: int`
- `items: list[RecommendationItem]` — jobs with salary data that pass the filter.
- `items_without_salary: list[RecommendationItem]` — jobs that pass every other filter
  but have no comparable salary. Empty when `salary_min` is absent.
- `total: int` — count of salary-qualified candidates, not the number returned.
- `without_salary_total: int` — count of candidates in the second bucket.
- `limit: int`
- `retrieval_version: str` (`"v1"`)

`RecommendationItem`:

- `job: JobRead`
- `score: float` — retrieval score, rounded to 4 decimals.
- `matched_skills: list[str]` — sorted canonical-skill overlap.

`items` and `items_without_salary` are each capped at `limit` independently. M4 merges
the two lists, reranks the merged pool, and re-partitions it by salary availability
before selecting the final results.

### Salary behavior

When `salary_min` is absent, every job ranks in `items`, including jobs with no salary.

When `salary_min` is present:

- Same-currency jobs with `salary_max >= salary_min` go to `items`.
- Same-currency jobs with a known salary below the floor are excluded.
- Jobs with missing salary bounds, or a different currency (no FX conversion), go to
  `items_without_salary`. They still compete on the same retrieval score within their
  bucket.

The UI labels the second bucket "Salary not mentioned."

### Ranking

1. Apply filters and drop jobs without a usable embedding.
2. Semantic score = cosine similarity between the resume vector and the job vector.
   Negative values are clamped to 0.
3. Skill score = share of the job's listed skills present in the resume's
   `canonical_skills`; 0 when the job lists no skills.
4. Final score = `0.85 × semantic + 0.15 × skill`, rounded to 4 decimals.
5. Tie-break: score descending, newest `posted_at`, lowest job id. Naive datetimes are
   treated as UTC.

Semantics dominate because titles vary; the exact-skill component improves recall for
jobs that name the same tools. The score is deliberately not called a fit score.

### Embedding text

`services/resumes.py` gains a public `resume_embed_text(profile)` used both at upload
and by retrieval when a stored resume has no vector. It includes summary, target roles,
canonical and display skills, preferred locations, experience titles/companies **and
highlights**, education, certifications, and projects. The M2 version omitted
highlights and certifications.

Existing resumes are re-embedded once with `python -m app.cli reembed`, which recomputes
and stores every resume vector. Job embedding text is unchanged.

### Missing or mismatched embeddings

- A resume with no stored vector is embedded from its profile, persisted, and used.
- Jobs with no vector are excluded from candidates and totals.
- Job vectors whose dimension differs from the resume vector are excluded rather than
  crashing the scan.

## Decisions left to the builder

- Exact SQL escaping helper for substring filters (must treat `%` and `_` literally).
- Whether `reembed` also reports skipped malformed profiles; v1 may skip and count.
- Internal dataclass names in the retrieval service; the plan fixes them.
- UI copy for the two salary buckets (M5).

## Tests

- Ranking: cosine order, skill boost, clamp at zero, tie-break, limit, totals.
- Filters: location (including `remote`), remote, experience tiers, role family and
  title fallback, salary buckets, currency mismatch, wildcard escaping.
- Robustness: unembedded jobs, mismatched dimensions, resume without an embedding,
  naive datetimes.
- API: response shape, 404, 422, default limit, filter pass-through, salary split.
- Tests use fake unit vectors and never load the embedding model.

## Rollout

No migration. Run `python -m app.cli reembed` once on the dev database, run `pytest`,
then exercise the endpoint against the dev server with a stored resume. Update
`PROGRESS.md` and commit locally; push at the milestone boundary only after the full
suite passes.
