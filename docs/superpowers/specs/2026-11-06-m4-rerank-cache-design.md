# M4 — Rerank and match cache

Date: 2026-11-06
Status: proposed

## Intent

M3 returns up to 40 semantically ranked candidates per salary bucket. That ranking
rewards wording overlap, not fit: a five-year role can outrank a perfect junior role
because its description echoes the resume. M4 adds the second stage of the funnel: a
local LLM reads compact resume and job cards, scores fit from 0 to 100, explains why
each job fits, names the skills a student is missing, and caches every judgment so a
repeat request spends no tokens.

The response returns up to 30 final results. It targets 20 salary-known jobs and 10
salary-unstated jobs, but backfills unused slots from whichever list is short, so a thin
bucket never leaves the result set half empty.

## Goals

- Rerank the merged M3 candidate pool with `lfm3:1.7b`, ten job cards per batch.
- Blend the LLM score with the retrieval score for final ordering and display.
- Return `reasons` and `gaps` per job.
- Cache every judgment in `matches`, keyed by resume, job, prompt, and model.
- Keep the endpoint useful when the reranker fails: retry once, degrade per item.
- Log Ollama prompt and completion token counts on every call.
- Preserve deterministic retrieval: `services/retrieval.py` stays LLM-free.
- Seed 3–5 jobs without salary so the unstated list is visible and testable in the demo.

## Non-goals

- Vector stores, pgvector, or any new dependency; the corpus is 100 seed jobs.
- Database schema changes.
- Frontend work (M5), auth, or live job sources.
- Storing retrieval scores in the cache (they are deterministic and cheap).
- Re-ranking across requests, background jobs, or cache eviction.

## Anti-goals

- A request failing because Ollama is down or a small model dropped an item.
- Showing a fit score the model did not produce without marking it degraded.
- Re-spending tokens for a `(resume, job, prompt, model)` already judged.
- Silently serving scores produced by a different model or prompt.

## Constraints

- Python 3.14, FastAPI, SQLModel, SQLite. No schema change; `matches` already exists.
- Every LLM call goes through `app/llm/client.py`, and the cache is checked first.
- A rerank response is untrusted until every requested `job_id` is present.
- Routers stay thin; business logic lives in `app/services/`.
- Local Ollama only; hosted or coding-plan endpoints are not used.
- No new dependency without asking.

## Approaches considered

1. **Final score: LLM alone versus blended (chosen: blended).** A 1.7B model is noisy
   and clusters around the middle of the scale; blending 70% LLM with 30% retrieval
   dampens that and keeps the semantic signal. The trade-off, accepted deliberately, is
   that the displayed number is no longer fully explained by the reasons — the UI must
   treat reasons as evidence, not a proof of the score.
2. **Cache key: add a `model` column versus encode the model in `prompt_version`
   (chosen: encode).** `rerank-v1@lfm3:1.7b` gets model-aware invalidation with no
   migration. The explicit column belongs in the Postgres schema later.
3. **Failure behaviour: fail the request versus always degrade versus hybrid (chosen:
   hybrid).** Retry each rejected batch once, degrade only the items that still failed,
   and mark them. A demo should not 500 because the local model hiccuped.
4. **Service layout: extend retrieval versus orchestrate in the router versus split
   services (chosen: split).** `services/rerank.py` and `services/recommend.py` keep
   retrieval deterministic and the router thin.
5. **Final count: a fixed split versus a 30-result budget with backfill (chosen:
   flexible 30).** The response targets 20 salary-known and 10 unstated, then fills
   unused slots from the other list when one is short. A fixed split would return fewer
   than 30 results on a thin corpus. This supersedes the M3 note that said "M4 will
   return the final 20".

## Design

### Public API

`GET /api/resumes/{resume_id}/recommendations` keeps its path, filters, and 404/422
behaviour.

Query parameters:

- Existing filters: `location`, `remote`, `experience_years`, `role`, `salary_min`.
- `limit: int` now caps the **total** final results, default `settings.final_top_k`
  (30), range 1–100.
- The split is derived from `limit`: `settings.unstated_target_share` (1/3) of the
  budget targets the unstated list, the rest targets salary-known. At the default 30,
  that is 20 known + 10 unstated.

`RecommendationList` additions:

- `rerank_status: "ok" | "partial" | "unavailable"`
- `rerank_version: str` — e.g. `"rerank-v1@lfm3:1.7b"`

`RecommendationItem` additions:

- `score: float` — blended score, 0–100, one decimal.
- `retrieval_score: float` — M3 score, 0–1, four decimals.
- `reasons: list[str]` — 1–3 short, concrete sentences from the model.
- `gaps: list[str]` — 1–3 missing skills or areas.
- `reranked: bool` — false when the item was degraded.
- `matched_skills` stays.

The merged reranked pool is always partitioned by salary status, with or without a
`salary_min` filter: `items` holds comparable-salary jobs, `items_without_salary` holds
jobs whose salary is missing or not comparable in the resume's currency (the M3
`_salary_is_unknown` rule). Selection takes each list's target, then backfills unused
slots from the other list up to `limit`; together the two lists contain at most `limit`
results. `total` and `without_salary_total` are recomputed from that partition as
candidate counts, not the M3 retrieval-bucket counts.

Known limitation: with no `salary_min`, M3 caps the mixed candidate pool at 40 before
M4 partitions it, so a corpus with many unstated-salary jobs could have too few of them
in the pool to fill the target. The committed corpus currently has complete INR
salaries on every job; M4 adds 3–5 jobs without salary so the second list is demoable.
Partitioning inside retrieval is out of scope.

### Seed data

Add 3–5 jobs to `data/seed_jobs.json` with no `salary_min` or `salary_max`, spread
across at least two role families and locations, with plausible junior-to-mid titles
and skills so they can rank. Keep fingerprints and external ids unique; ingestion stays
idempotent. Exact jobs are left to the builder.

### Scoring

- `retrieval_score` = M3 score (`0.85 × cosine + 0.15 × skill share`), 0–1.
- `llm_score` = model score, integer 0–100.
- `blended = clamp(0.7 × llm_score + 0.3 × retrieval_score × 100, 0, 100)`, rounded to
  one decimal. Weights are settings: `rerank_llm_weight` (0.7) and the remainder.
- Ordering: blended descending (unrounded), then retrieval descending, then newest
  `posted_at`, then job id.
- A degraded item gets `blended = retrieval_score × 100`, empty reasons and gaps, and
  `reranked = false`.
- Only `llm_score` is cached; the blend is computed at read time, so weight changes do
  not invalidate anything.

### Rerank pipeline

`app/services/rerank.py`:

- Signature: `rerank_candidates(session, resume, jobs, *, client=None) ->
  RerankOutcome`, where `RerankOutcome` maps `job_id` to `(llm_score, reasons, gaps,
  reranked)` and exposes a status.
- The two M3 buckets are merged into one deduplicated list before batching; results are
  split back by job id.
- **Resume card** (≤ 800 chars): summary, total years, seniority, target roles,
  preferred locations, remote preference, salary expectation and currency, canonical
  skills, and the two most recent role titles.
- **Job card**: id, title, company, location, remote, seniority, salary range and
  currency, skills, and a description excerpt capped at 400 chars.
- **Prompt**: instructs the model to use anchored bands (90–100 strong fit, 70–89 good,
  50–69 stretch, 30–49 weak, 0–29 poor), return 1–3 reasons and 1–3 gaps, judge
  seniority and domain honestly, and never invent facts. Output is a JSON object with
  a `results` array of `job_id`, `score`, `reasons`, `gaps`, constrained by a JSON
  schema. An object root is more reliable with Ollama's schema-constrained generation
  than a bare array.
- **Batching**: `settings.rerank_batch_size` (10). Batches run sequentially; Ollama
  serves one request at a time well and this keeps memory and logs predictable.

### Validation and degradation

A batch response is rejected unless:

- it parses as a JSON list;
- its `job_id`s exactly equal the requested set — no missing, duplicate, or unknown ids;
- every `score` is numeric in 0–100 (rounded to an integer);
- `reasons` and `gaps` each contain 1–3 non-empty strings (each ≤ 200 chars); longer
  lists are truncated, empty ones reject the batch.

On rejection, retry the batch once with the validation error appended to the prompt. If
the retry also fails, degrade that batch's items. Any `httpx.HTTPError` — connection
failure, timeout, or an HTTP 4xx/5xx from Ollama — stops the remaining batches for this
request and degrades them, so a crashed model does not cost eight timeouts.

Status for the returned set: `ok` when every returned item has a cached or fresh LLM
score, `partial` when some are degraded, `unavailable` when none could be reranked. An
empty candidate pool is `ok`: there was nothing to rerank and nothing failed.

### Cache

- Version string: `f"rerank-v1@{settings.llm_rerank_model}"`.
- Before any model call, load `Match` rows for `resume_id`, the candidate job ids, and
  that `prompt_version`. Hits skip the model and count as reranked.
- After each successful batch, upsert one `Match` per job: `score` (LLM score),
  `reasons`, `gaps`, `model`, `prompt_version`. Degraded items are not cached.
- The unique constraint `(resume_id, job_id, prompt_version)` is unchanged. Changing
  the model or the prompt changes the version string, so stale scores miss instead of
  being reused.
- Seed jobs are immutable in practice; cache invalidation on job edits is out of scope.

### Orchestration

`app/services/recommend.py` exposes `recommend_jobs(session, resume, filters, limit)`.
It calls `retrieve_jobs` (M3), reranks the merged pool, blends and sorts, partitions by
salary status, applies the target split, backfills unused slots from the other list up
to `limit`, and returns a result object. The router only validates input and maps the
result to schemas.

Selection arithmetic, for clarity:

1. `unstated_target = min(round(limit × unstated_target_share), len(unstated))`.
2. `known_target = min(limit − unstated_target, len(known))`.
3. If `known` was short, give the remaining `limit − known_target − unstated_target`
   slots to `unstated` while candidates remain. Total never exceeds `limit`.

Step 2 is what makes backfilling automatic in the other direction: when `unstated` is
short, `known_target` grows to absorb the difference. Rounding on the share (rather
than ceiling the complement) avoids floating-point drift at the default 30.

### Token logging

`app/llm/client.py` gains an optional `purpose` argument (e.g. `"parse"`, `"rerank"`)
on `complete` and `complete_json`. The Ollama branch reads `prompt_eval_count`,
`eval_count`, and `total_duration` from the response body and emits one INFO log line:

```
llm_call model=lfm3:1.7b purpose=rerank prompt_tokens=812 completion_tokens=143 total_ms=2140
```

Missing fields are logged as `-`. Nothing is persisted and no dependency is added.
There is no token logging for the non-Ollama branches, which are unused by default.

### Configuration

New settings (and `env.example`):

- `final_top_k: int = 30` — total final results.
- `unstated_target_share: float = 0.3333` — share of that total targeting the
  unstated list.
- `rerank_llm_weight: float = 0.7`

Unchanged: `top_k = 40` (retrieval pool), `rerank_batch_size = 10`,
`llm_rerank_model = lfm3:1.7b`.

### Testing

- Rerank: card rendering, batch size, prompt version, validation failures (missing,
  duplicate, unknown id, out-of-range score, malformed lists), retry-then-success,
  retry-then-degrade, short-circuit when the model is down.
- Cache: hit skips the client, miss writes a `Match`, a second call reuses it, a
  different model misses.
- Scoring/selection: blend arithmetic, rounding, ordering, tie-break, target split,
  backfill in both directions, degraded score.
- API: new fields, statuses, default limit 30, 20/10 target split, backfill, 404/422,
  filters, and partitioning when no salary filter is present.
- Seed data: ingestion loads the new no-salary jobs, and they appear in
  `items_without_salary` under the backfill rule.
- Logging: `caplog` captures the token counts from a fake Ollama response.
- Existing M3 tests change only where the contract changed (default limit, score
  meaning). No test is deleted or weakened; retrieval service tests stay as they are.

Verification: `pytest` (targeted with `-q`, then the full suite), `python -m app.cli
ingest`, and a manual timing of a first and a cached request against the seed corpus.

## Risks

- Eight sequential batches (80 candidates) may make the first request slow. Measure;
  only add concurrency if the demo feels slow, as a separate change.
- A 1.7B model may still produce coarse or clustered scores. The rubric and degradation
  path contain the damage; prompt tuning is cheap because the cache is versioned.
- Rerank quality depends on seed descriptions, which are short. This is a demo corpus
  limitation, not a pipeline bug.

## What is left to the builder

Prompt wording, card formatting, helper names, log formatting, and test fixture shape,
provided the contracts above hold. The `retrieval_score` and `reranked` fields are for
debugging and UI honesty; M5 decides how to present them.

## Docs to update with the implementation

- `PROGRESS.md` invariant 10: up to 30 final results, targeting 20 known + 10 unstated
  with backfill.
- M3 spec lines 52 and 112, noting the flexible-30 decision supersedes "final 20".
- `backend/env.example` with the new settings.
- `data/seed_jobs.json`: 3–5 jobs without salary bounds.
