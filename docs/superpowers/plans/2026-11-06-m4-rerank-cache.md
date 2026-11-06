# M4 Rerank and Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-LLM rerank stage with a model-aware cache, blended scoring, reasons/gaps, hybrid degradation, and flexible 30-result responses.

**Architecture:** `services/rerank.py` renders compact cards, batches ten jobs, strictly validates every response, retries once, and reads/writes `matches`. `services/recommend.py` orchestrates retrieval → rerank → blend → salary partition → selection. The router stays thin, and `llm/client.py` logs Ollama token counts.

**Tech Stack:** Python 3.14, FastAPI, SQLModel/SQLite, httpx, pytest, local Ollama (`lfm3:1.7b`).

**Spec:** `docs/superpowers/specs/2026-11-06-m4-rerank-cache-design.md`

## Global Constraints

- Python 3.14, FastAPI, SQLModel, SQLite. No new dependency.
- No schema change; reuse `matches` with unique `(resume_id, job_id, prompt_version)`.
- Every LLM call goes through `app/llm/client.py`; check the cache before spending tokens.
- Prompt version is `f"rerank-v1@{settings.llm_rerank_model}"`.
- Blend: `clamp(0.7 × llm_score + 0.3 × retrieval_score × 100, 0, 100)`, round to one decimal.
- Default response: up to 30 total, target 20 salary-known + 10 unstated, backfill both ways.
- A rerank response is valid only when every requested job id appears exactly once, each
  score is numeric 0–100, and `reasons`/`gaps` each contain at least one non-empty
  string; longer lists truncate to three.
- Local Ollama only. Never point `LLM_BASE_URL` at a hosted or coding-plan endpoint.
- No test may be deleted, skipped, or weakened.

## Review Focus

1. Model returns valid JSON for the wrong id set (missing, duplicate, or unknown) →
   batch rejected, items degraded; no score is attached to the wrong job.
2. Score arrives as a JSON string or float (`"82"`, `82.6`) → rejected consistently,
   never a crash or silent wrap.
3. Identical blended scores and posted dates → deterministic tie-break (retrieval score,
   posted_at, job id) and a stable order across calls.
4. Cache row written under another model or prompt → cache miss; a cached row for a job
   outside today's pool never leaks in.
5. Every comparable-salary job is below the floor and only unstated jobs remain →
   unstated list fills and the response is not empty when candidates exist.

## File Structure

- `backend/app/llm/client.py` — add `purpose` and Ollama token logging.
- `backend/app/services/rerank.py` (new) — cards, prompt, batching, validation, cache.
- `backend/app/services/recommend.py` (new) — retrieval → rerank → blend → selection.
- `backend/app/services/resume_parse.py` — label parse calls with `purpose="parse"`.
- `backend/app/services/retrieval.py` — expose `salary_is_unknown()`.
- `backend/app/config.py` — final count, share, and blend weight settings.
- `backend/app/schemas.py` — response fields.
- `backend/app/routers/recommendations.py` — call the orchestration service.
- `backend/env.example` — document the new settings.
- `data/seed_jobs.json` — add five jobs without salary.
- Tests: `backend/tests/test_llm_client.py`, `test_rerank.py` (new),
  `test_recommend.py` (new), `test_recommendations_api.py`, `test_seed_corpus.py` (new).

---

### Task 1: Log Ollama token counts

**Files:**
- Modify: `backend/app/llm/client.py`
- Modify: `backend/app/services/resume_parse.py:59-67`
- Test: `backend/tests/test_llm_client.py`

**Interfaces:**
- Produces: `LLMClient.complete(..., purpose: str = "") -> str` and
  `LLMClient.complete_json(..., purpose: str = "") -> object`.
- Produces: one INFO line on logger `app.llm.client` per Ollama call:
  `llm_call model=<model> purpose=<purpose|-> prompt_tokens=<n|-> completion_tokens=<n|-> total_ms=<n|->`.

- [ ] **Step 1: Write the failing test**

```python
import logging


def test_ollama_token_counts_are_logged(monkeypatch, caplog):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {"content": '{"name": "Priya"}'},
                "prompt_eval_count": 812,
                "eval_count": 143,
                "total_duration": 2_140_000_000,
            }

    monkeypatch.setattr("app.llm.client.httpx.post", lambda *a, **k: FakeResponse())
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    with caplog.at_level(logging.INFO, logger="app.llm.client"):
        client.complete_json("system", "user", model="lfm3:1.7b", purpose="rerank")
    assert (
        "llm_call model=lfm3:1.7b purpose=rerank "
        "prompt_tokens=812 completion_tokens=143 total_ms=2140"
    ) in caplog.text
```

Also add a test that a response without token fields logs `-` instead of raising:

```python
def test_missing_token_fields_log_dashes(monkeypatch, caplog):
    capture_post(monkeypatch)  # existing helper; FakeResponse has no token fields
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    with caplog.at_level(logging.INFO, logger="app.llm.client"):
        client.complete_json("system", "user", model="lfm3:1.7b")
    assert "prompt_tokens=- completion_tokens=- total_ms=-" in caplog.text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_llm_client.py -q`
Expected: FAIL — `complete_json()` got an unexpected keyword argument `purpose`.

- [ ] **Step 3: Implement `purpose` and logging**

Add `import logging` and module-level `logger = logging.getLogger(__name__)`. Thread
`purpose: str = ""` through `complete()` and `complete_json()`; `complete_json` forwards
it to `complete()`. In `_ollama`, read the response body once:

```python
data = response.json()
prompt_tokens = data.get("prompt_eval_count", "-")
completion_tokens = data.get("eval_count", "-")
nanos = data.get("total_duration")  # Ollama reports nanoseconds
total_ms = round(nanos / 1_000_000) if isinstance(nanos, int) else "-"
logger.info(
    "llm_call model=%s purpose=%s prompt_tokens=%s completion_tokens=%s total_ms=%s",
    model, purpose or "-", prompt_tokens, completion_tokens, total_ms,
)
return data.get("message", {}).get("content", "")
```

Pass `purpose="parse"` from `_attempt()` in `resume_parse.py`. Leave the Anthropic and
OpenAI branches unchanged (no token logging there).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_llm_client.py tests/test_resume_parse.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/client.py backend/app/services/resume_parse.py backend/tests/test_llm_client.py
git commit -m "feat(llm): log ollama token counts per call"
```

---

### Task 2: Rerank core — cards, batching, strict validation, degradation

**Files:**
- Create: `backend/app/services/rerank.py`
- Test: `backend/tests/test_rerank.py`

**Interfaces:**
- Produces: `prompt_version(model: str) -> str`.
- Produces: `RerankValidationError(ValueError)`.
- Produces: `@dataclass(frozen=True) RerankResult(score: int, reasons: list[str],
  gaps: list[str], reranked: bool)`.
- Produces: `@dataclass(frozen=True) RerankOutcome(results: dict[int, RerankResult],
  status: Literal["ok", "partial", "unavailable"])`.
- Produces: `rerank_jobs(session: Session, resume: Resume, jobs: list[Job], *,
  client: LLMClient | None = None) -> RerankOutcome` — every input job id is present in
  `results`, degraded when the model failed.
- Produces: private helpers `_job_card(job: Job) -> str`, `_resume_card(profile:
  ResumeProfile) -> str`, `_validate_batch(raw: object, requested_ids: set[int]) ->
  dict[int, RerankResult]`.
- Consumes: nothing from other tasks. Task 3 adds the cache to this function.

- [ ] **Step 1: Write the failing card tests**

```python
from app.services.rerank import _job_card, _resume_card, prompt_version
from tests.factories import make_job, make_profile


def test_prompt_version_includes_model():
    assert prompt_version("lfm3:1.7b") == "rerank-v1@lfm3:1.7b"


def test_job_card_is_compact_and_marks_salary():
    job = make_job(id=7, description="y" * 600)
    card = _job_card(job)
    assert card.startswith("JOB 7")
    assert "y" * 400 in card
    assert "y" * 401 not in card
    assert "Salary: 1200000-1800000 INR" in card


def test_job_card_marks_missing_salary():
    job = make_job(id=8, salary_min=None, salary_max=None)
    assert "Salary: not stated" in _job_card(job)


def test_resume_card_is_bounded():
    card = _resume_card(make_profile())
    assert len(card) <= 800
    assert "1.5 years" in card
    assert "python" in card
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: FAIL — module `app.services.rerank` does not exist.

- [ ] **Step 3: Implement the cards and `prompt_version`**

Render the job card exactly as:

```
JOB {job.id}
Title: {title}
Company: {company}
Location: {location} (remote: yes|no)
Seniority: {seniority}
Salary: {min}-{max} {currency}   |   Salary: not stated
Skills: {comma-joined skills or "none"}
Description: {description[:400]}
```

Render the resume card from the profile: summary (first 200 chars), total years and
seniority, target roles, preferred locations plus remote preference, salary expectation
with currency (or "not stated"), canonical skills, and at most two recent role titles.
Cap the assembled card at 800 characters.

- [ ] **Step 4: Run the card tests to verify they pass**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: PASS.

- [ ] **Step 5: Write the failing pipeline tests**

Add these helpers and tests. `FakeClient` records each user prompt and returns queued
responses or raises queued exceptions.

```python
import re

import httpx
import numpy as np

from app.embeddings import to_bytes
from app.models import Resume
from app.services.rerank import RerankOutcome, rerank_jobs
from tests.factories import make_job, make_profile


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete_json(self, system, user, *, model, max_tokens=1024,
                      json_schema=None, purpose=""):
        self.calls.append(user)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def add_resume(session):
    profile = make_profile()
    resume = Resume(filename="priya.txt", text="Priya", profile=profile.model_dump(),
                    embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
                    content_hash="rerank-resume")
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


def add_jobs(session, count, **overrides):
    jobs = []
    for index in range(count):
        job = make_job(title=f"AI Engineer {index}", **overrides)
        session.add(job)
        jobs.append(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return jobs


def valid_response(ids):
    return {"results": [
        {"job_id": job_id, "score": 80, "reasons": ["Fits the role."],
         "gaps": ["Add testing depth."]}
        for job_id in ids
    ]}


def batch_ids(prompt):
    return sorted(int(value) for value in re.findall(r"JOB (\d+)", prompt))


def test_batches_ten_jobs_and_covers_every_id(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 23)
    client = FakeClient(*(
        valid_response([job.id for job in jobs[start:start + 10]])
        for start in range(0, 23, 10)
    ))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert [len(batch_ids(call)) for call in client.calls] == [10, 10, 3]
    assert set(outcome.results) == {job.id for job in jobs}
    assert all(result.reranked for result in outcome.results.values())
    assert outcome.status == "ok"


def test_missing_id_retries_once_then_succeeds(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 2)
    ids = [job.id for job in jobs]
    client = FakeClient(valid_response(ids[:1]), valid_response(ids))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 2
    assert set(outcome.results) == set(ids)
    assert outcome.status == "ok"


def test_duplicate_or_unknown_id_rejects_and_degrades_after_retry(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 2)
    ids = [job.id for job in jobs]
    bad = {"results": [
        {"job_id": ids[0], "score": 80, "reasons": ["a"], "gaps": ["b"]},
        {"job_id": ids[0], "score": 90, "reasons": ["a"], "gaps": ["b"]},
    ]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 2
    assert all(not result.reranked for result in outcome.results.values())
    assert outcome.status == "unavailable"


def test_string_score_rejects_batch(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    bad = {"results": [{"job_id": jobs[0].id, "score": "82",
                        "reasons": ["a"], "gaps": ["b"]}]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.results[jobs[0].id].reranked is False


def test_empty_reasons_rejects_batch(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    bad = {"results": [{"job_id": jobs[0].id, "score": 82,
                        "reasons": [], "gaps": ["b"]}]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.results[jobs[0].id].reranked is False


def test_long_lists_are_truncated_to_three(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    response = {"results": [{
        "job_id": jobs[0].id, "score": 82,
        "reasons": ["r1", "r2", "r3", "r4", "r5"],
        "gaps": ["g1", "g2", "g3", "g4"],
    }]}
    outcome = rerank_jobs(session, resume, jobs, client=FakeClient(response))
    result = outcome.results[jobs[0].id]
    assert result.reranked is True
    assert result.reasons == ["r1", "r2", "r3"]
    assert result.gaps == ["g1", "g2", "g3"]


def test_http_error_degrades_all_and_stops_calling(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 12)
    client = FakeClient(httpx.ConnectError("down"))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 1
    assert len(outcome.results) == 12
    assert outcome.status == "unavailable"


def test_partial_status_when_one_batch_fails(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 12)
    ids = [job.id for job in jobs]
    client = FakeClient(valid_response(ids[:10]), httpx.ConnectError("down"))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.status == "partial"
    assert sum(result.reranked for result in outcome.results.values()) == 10


def test_empty_job_list_is_ok(session):
    resume = add_resume(session)
    client = FakeClient()
    outcome = rerank_jobs(session, resume, [], client=client)
    assert outcome.results == {}
    assert outcome.status == "ok"
    assert client.calls == []
```

- [ ] **Step 6: Run them to verify they fail**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: FAIL — `rerank_jobs` is not defined.

- [ ] **Step 7: Implement the pipeline**

Define a module-level `RERANK_SCHEMA` object-root schema:

```python
RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "reasons": {"type": "array", "items": {"type": "string"}},
                    "gaps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["job_id", "score", "reasons", "gaps"],
            },
        }
    },
    "required": ["results"],
}
```

Prompt requirements: rate fit 0–100 with the anchored bands, judge seniority and domain
honestly, give 1–3 concrete reasons and 1–3 gaps, never invent facts, and emit one entry
per `JOB` id with no extras.

`_validate_batch` raises `RerankValidationError(ValueError)` when the root is not an
object with a `results` list, any entry is missing a key, `job_id`/`score` is a `bool`
or non-numeric type, `score` is outside 0–100, or reasons/gaps are empty. Accept int and
float scores (round floats to the nearest integer); truncate reasons/gaps to three
entries and each string to 200 characters.

`rerank_jobs` loop:

1. Chunk jobs by `get_settings().rerank_batch_size`.
2. Call `client.complete_json(system, user, model=settings.llm_rerank_model,
   max_tokens=2048, json_schema=RERANK_SCHEMA, purpose="rerank")`.
3. On `RerankValidationError` or `LLMError`, retry once with
   `f"\n\nThe previous response failed validation: {exc}"` appended to the user prompt.
4. If the retry still fails validation, degrade every job in that batch.
5. On `httpx.HTTPError` (connection, timeout, or HTTP status), degrade every remaining
   job and stop issuing calls.
6. Degraded result = `RerankResult(score=0, reasons=[], gaps=[], reranked=False)`.
7. Status: `ok` for no jobs or no degraded items, `unavailable` when none reranked,
   otherwise `partial`.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/rerank.py backend/tests/test_rerank.py
git commit -m "feat(backend): rerank jobs with strict batch validation"
```

---

### Task 3: Cache rerank judgments

**Files:**
- Modify: `backend/app/services/rerank.py`
- Test: `backend/tests/test_rerank.py`

**Interfaces:**
- Consumes: `prompt_version`, `RerankResult`, `RerankOutcome`, `_validate_batch`.
- Produces: private helpers `_cached_results(session, resume_id, job_ids,
  version) -> dict[int, RerankResult]` and `_store_results(session, resume_id, results,
  model, version) -> None`.
- Behavior: a cached hit skips the model and counts as reranked; successful fresh
  batches are upserted; degraded items are never cached.

- [ ] **Step 1: Write the failing cache tests**

```python
from sqlmodel import select

from app.config import get_settings
from app.models import Match
from app.services.rerank import prompt_version


def cache_match(session, resume, job, *, version, score=91):
    row = Match(resume_id=resume.id, job_id=job.id, score=score,
                reasons=["cached reason"], gaps=["cached gap"],
                model="lfm3:1.7b", prompt_version=version)
    session.add(row)
    session.commit()
    return row


def test_cached_match_skips_the_model(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 2)
    version = prompt_version(get_settings().llm_rerank_model)
    cache_match(session, resume, jobs[0], version=version)
    client = FakeClient(valid_response([jobs[1].id]))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 1
    assert batch_ids(client.calls[0]) == [jobs[1].id]
    assert outcome.results[jobs[0].id].score == 91
    assert outcome.results[jobs[0].id].reasons == ["cached reason"]
    assert outcome.results[jobs[0].id].reranked is True


def test_successful_batch_is_cached(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    outcome = rerank_jobs(session, resume, jobs,
                          client=FakeClient(valid_response([jobs[0].id])))
    stored = session.exec(
        select(Match).where(Match.resume_id == resume.id, Match.job_id == jobs[0].id)
    ).one()
    assert stored.score == 80
    assert stored.reasons == ["Fits the role."]
    assert stored.prompt_version == prompt_version(get_settings().llm_rerank_model)
    assert outcome.results[jobs[0].id].reranked is True


def test_other_model_version_is_a_miss(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    cache_match(session, resume, jobs[0], version="rerank-v1@other:1b", score=12)
    client = FakeClient(valid_response([jobs[0].id]))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 1
    assert outcome.results[jobs[0].id].score == 80


def test_degraded_items_are_not_cached(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    rerank_jobs(session, resume, jobs,
                client=FakeClient(httpx.ConnectError("down")))
    assert session.exec(select(Match)).all() == []
```

Import `select` from `sqlmodel` and drop the `session.get` line above when writing the
real test.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: FAIL — cached jobs are still sent to the model / no `Match` rows are written.

- [ ] **Step 3: Implement cache read and write**

Version = `prompt_version(get_settings().llm_rerank_model)`. Before batching, load
`Match` rows for `resume.id`, the job ids, and that version; convert each to
`RerankResult(score=row.score, reasons=row.reasons, gaps=row.gaps, reranked=True)`.
Rerank only the remaining jobs. After each successful batch, upsert one `Match` per
result with `model=settings.llm_rerank_model`, `prompt_version=version`, then
`session.commit()`. Never write degraded results. Cached results count toward
`reranked` when computing status.

- [ ] **Step 4: Run the full rerank suite to verify it passes**

Run: `cd backend && pytest tests/test_rerank.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rerank.py backend/tests/test_rerank.py
git commit -m "feat(backend): cache rerank judgments by prompt and model"
```

---

### Task 4: Blend, partition, and select in `recommend.py`

**Files:**
- Create: `backend/app/services/recommend.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/retrieval.py` (rename `_salary_is_unknown` to
  `salary_is_unknown` and update its two call sites)
- Modify: `backend/env.example`
- Test: `backend/tests/test_recommend.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) RecommendedJob(job: Job, retrieval_score: float,
  score: float, matched_skills: list[str], reasons: list[str], gaps: list[str],
  reranked: bool)`.
- Produces: `@dataclass(frozen=True) RecommendationResult(items: list[RecommendedJob],
  items_without_salary: list[RecommendedJob], total: int, without_salary_total: int,
  rerank_status: str, rerank_version: str)`.
- Produces: `recommend_jobs(session: Session, resume: Resume, *, filters:
  RetrievalFilters | None = None, limit: int | None = None, client: LLMClient | None =
  None) -> RecommendationResult`.
- Produces: `blend_score(llm_score: int, retrieval_score: float, weight: float) -> float`.
- Consumes: `retrieve_jobs`, `salary_is_unknown`, `rerank_jobs`, `prompt_version`.
- Settings: `final_top_k: int = 30`, `unstated_target_share: float = 0.3333`,
  `rerank_llm_weight: float = 0.7`.

- [ ] **Step 1: Add the settings and the env example**

In `Settings`, add `final_top_k: int = 30`, `unstated_target_share: float = 0.3333`,
and `rerank_llm_weight: float = 0.7`. In `backend/env.example`, under Retrieval:

```
FINAL_TOP_K=30
UNSTATED_TARGET_SHARE=0.3333
RERANK_LLM_WEIGHT=0.7
```

- [ ] **Step 2: Write the failing blend and selection tests**

```python
import numpy as np

from app.embeddings import to_bytes
from app.models import Resume
from app.services.recommend import blend_score, recommend_jobs
from app.services.rerank import RerankOutcome, RerankResult
from app.services.retrieval import Candidate, RetrievalResult
from tests.factories import make_job, make_profile


def add_resume(session):
    profile = make_profile()
    resume = Resume(filename="priya.txt", text="Priya", profile=profile.model_dump(),
                    embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
                    content_hash="recommend-resume")
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


def add_job(session, **overrides):
    job = make_job(**overrides)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def add_jobs(session, count, **overrides):
    title = overrides.pop("title", "Job")
    return [add_job(session, title=f"{title} {index}", **overrides)
            for index in range(count)]


def candidate(job, score):
    return Candidate(job=job, score=score, matched_skills=[])


def retrieval(paid, unknown=()):
    return RetrievalResult(items=list(paid), items_without_salary=list(unknown),
                           total=len(paid), without_salary_total=len(unknown))


def rerank_all(jobs, score=80, reranked=True):
    return RerankOutcome(
        results={job.id: RerankResult(score=score, reasons=["fits"], gaps=["gap"],
                                      reranked=reranked) for job in jobs},
        status="ok" if reranked else "unavailable",
    )


def test_blend_is_seventy_thirty():
    assert blend_score(80, 0.5, 0.7) == 71.0


def test_blend_endpoints():
    assert blend_score(100, 0.0, 0.7) == 70.0
    assert blend_score(0, 1.0, 0.7) == 30.0


def test_ordering_uses_blended_score(session, monkeypatch):
    resume = add_resume(session)
    low_llm = add_job(session, title="Low", embedding=None)
    high_llm = add_job(session, title="High", embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(low_llm, 0.9),
                                                   candidate(high_llm, 0.4)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            low_llm.id: RerankResult(60, ["a"], ["b"], True),
                            high_llm.id: RerankResult(90, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [high_llm.id, low_llm.id]


def test_equal_blends_fall_back_to_retrieval_score(session, monkeypatch):
    resume = add_resume(session)
    lower = add_job(session, title="Lower retrieval", embedding=None)
    higher = add_job(session, title="Higher retrieval", embedding=None)
    monkeypatch.setattr("app.services.recommend.blend_score", lambda *a, **k: 50.0)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(lower, 0.4),
                                                   candidate(higher, 0.7)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            lower.id: RerankResult(80, ["a"], ["b"], True),
                            higher.id: RerankResult(70, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [higher.id, lower.id]


def test_equal_everything_falls_back_to_job_id(session, monkeypatch):
    resume = add_resume(session)
    first = add_job(session, title="First", embedding=None)
    second = add_job(session, title="Second", embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(second, 0.5),
                                                   candidate(first, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            first.id: RerankResult(80, ["a"], ["b"], True),
                            second.id: RerankResult(80, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == sorted([first.id, second.id])
```

Selection tests (load 25 known-salary and 15 unstated jobs, all reranked at 80):

```python
def seed_partition(session, known, unstated):
    resume = add_resume(session)
    known_jobs = add_jobs(session, known, title="Known")
    unstated_jobs = add_jobs(session, unstated, title="Unstated",
                             salary_min=None, salary_max=None)
    paid = [candidate(job, 0.5) for job in known_jobs]
    unknown = [candidate(job, 0.5) for job in unstated_jobs]
    return resume, known_jobs, unstated_jobs, paid, unknown


def test_default_split_is_twenty_known_ten_unstated(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 25, 15)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (20, 10)


def test_unstated_is_short_known_backfills(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 30, 3)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (27, 3)


def test_known_is_short_unstated_backfills(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 15, 25)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (15, 15)


def test_limit_scales_the_target(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 25, 15)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume, limit=6)
    assert (len(result.items), len(result.items_without_salary)) == (4, 2)
```

Degradation and partition tests:

```python
def test_degraded_item_uses_retrieval_score_and_empty_explanations(session, monkeypatch):
    resume = add_resume(session)
    job = add_job(session, embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(job, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(
                            results={job.id: RerankResult(0, [], [], False)},
                            status="unavailable"))
    item = recommend_jobs(session, resume).items[0]
    assert item.score == 50.0
    assert item.reasons == [] and item.gaps == []
    assert item.reranked is False


def test_unstated_jobs_move_out_of_items_without_a_salary_filter(session, monkeypatch):
    resume = add_resume(session)
    known = add_job(session, embedding=None)
    unknown = add_job(session, embedding=None, salary_min=None, salary_max=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(known, 0.5),
                                                   candidate(unknown, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: rerank_all([known, unknown]))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [known.id]
    assert [item.job.id for item in result.items_without_salary] == [unknown.id]
    assert (result.total, result.without_salary_total) == (1, 1)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd backend && pytest tests/test_recommend.py -q`
Expected: FAIL — module `app.services.recommend` does not exist.

- [ ] **Step 4: Implement `recommend.py`**

Orchestration:

1. `limit = limit if limit is not None else settings.final_top_k`.
2. `retrieval_result = retrieve_jobs(session, resume, filters=filters, limit=settings.top_k)`.
3. Merge `items + items_without_salary`, dedupe by job id, and call
   `rerank_jobs(session, resume, jobs, client=client)`.
4. Build `RecommendedJob` for every candidate: `retrieval_score = round(c.score, 4)`;
   reranked → `blend_score(rr.score, c.score, settings.rerank_llm_weight)`; degraded →
   `round(c.score * 100, 1)`, empty reasons/gaps.
5. Partition with `salary_is_unknown(job, resume_currency)`, where `resume_currency =
   (ResumeProfile.model_validate(resume.profile).currency or "INR").upper()`.
6. Sort each list by `(-score, -retrieval_score, -posted_timestamp, job.id)`; reuse the
   retrieval module's posted-timestamp helper or duplicate the three-line conversion.
7. Select with the spec arithmetic: `unstated_target = min(round(limit * share),
   len(unstated))`; `known_target = min(limit - unstated_target, len(known))`; then give
   `limit - known_target - unstated_target` leftover slots to unstated while available.
8. `total = len(known)`, `without_salary_total = len(unstated)` from the partition.
9. `rerank_status = outcome.status`, `rerank_version = prompt_version(settings.llm_rerank_model)`.

- [ ] **Step 5: Run the recommend and retrieval suites**

Run: `cd backend && pytest tests/test_recommend.py tests/test_retrieval.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommend.py backend/app/config.py backend/env.example \
  backend/app/services/retrieval.py backend/tests/test_recommend.py
git commit -m "feat(backend): blend rerank and retrieval scores with flexible selection"
```

---

### Task 5: Expose the new contract through the API

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/recommendations.py`
- Modify: `backend/tests/test_recommendations_api.py`

**Interfaces:**
- `RecommendationItem` gains `retrieval_score: float`, `reasons: list[str]`,
  `gaps: list[str]`, `reranked: bool`; `score` is now the blended score.
- `RecommendationList` gains `rerank_status: Literal["ok", "partial", "unavailable"]`
  and `rerank_version: str`.
- Router calls `recommend_jobs(session, resume, filters=..., limit=resolved_limit)`
  where `resolved_limit = limit or settings.final_top_k`.

- [ ] **Step 1: Add the schema fields**

Apply the two interface changes above. Keep `JobRead`, totals, `retrieval_version`, and
`matched_skills` unchanged.

- [ ] **Step 2: Write the updated API tests**

Replace the retrieval-only assertions with the reranked contract. Add an autouse fake
client so the API tests never contact Ollama:

```python
import re

import pytest


@pytest.fixture(autouse=True)
def fake_rerank_client(monkeypatch):
    class FakeRerankClient:
        def complete_json(self, system, user, *, model, max_tokens=1024,
                          json_schema=None, purpose=""):
            ids = [int(value) for value in re.findall(r"JOB (\d+)", user)]
            return {"results": [
                {"job_id": job_id, "score": 80,
                 "reasons": ["Matches the target role."],
                 "gaps": ["Add production testing depth."]}
                for job_id in ids
            ]}

    monkeypatch.setattr("app.services.rerank.LLMClient", FakeRerankClient)
```

Update existing tests:

- `test_returns_ranked_recommendations`: `limit == 30`, `rerank_status == "ok"`,
  `rerank_version == prompt_version(get_settings().llm_rerank_model)`, item has
  `reasons`, `gaps`, `reranked`, `retrieval_score`, and no `text` in `job`.
- `test_limit_is_respected`: unchanged behaviour, `limit=1` → one item.
- `test_default_limit_is_the_configured_top_k` → rename
  `test_default_limit_is_final_top_k`; 41 jobs → 30 items, `total == 41`.
- `test_salary_split_is_exposed`: still one paid + one unstated.
- Add `test_unstated_jobs_are_visible_without_a_salary_filter`: one known and one
  no-salary job, no query params → one item each list.
- Add `test_unstated_backfills_when_known_is_short`: 1 known + 12 unstated, no filter →
  `len(items) == 1`, `len(items_without_salary) == 12`.
- Add `test_rerank_fields_are_present`: assert the four item fields and two top-level
  fields exist with the expected types.
- Keep `test_missing_resume_returns_404` and parameterized 422 cases (including
  `limit=101`).

- [ ] **Step 3: Run the API tests to verify they fail**

Run: `cd backend && pytest tests/test_recommendations_api.py -q`
Expected: FAIL — response lacks the new fields / router still uses retrieval.

- [ ] **Step 4: Update the router**

Keep validation thin: resolve the resume (404), call `recommend_jobs`, and map
`RecommendedJob` values to `RecommendationItem`. Do not re-implement filtering, sorting,
or selection in the router.

- [ ] **Step 5: Run the API tests to verify they pass**

Run: `cd backend && pytest tests/test_recommendations_api.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/recommendations.py backend/tests/test_recommendations_api.py
git commit -m "feat(api): return reranked recommendations with explanations"
```

---

### Task 6: Add no-salary seed jobs

**Files:**
- Modify: `data/seed_jobs.json`
- Create: `backend/tests/test_seed_corpus.py`

**Interfaces:**
- Consumes: `SeedSource`, `build_job`, `ingest_raw`.
- Produces: five jobs (`demo-101` … `demo-105`) with `salary_min` and `salary_max`
  omitted, unique ids/fingerprints, two or more role families and locations, and
  descriptions that do not mention compensation.

- [ ] **Step 1: Write the failing corpus test**

```python
from app.config import get_settings
from app.services.ingest import build_job, ingest_raw
from app.sources.base import JobQuery
from app.sources.seed import SeedSource


def test_seed_corpus_has_unstated_salary_jobs():
    raw_jobs = SeedSource(get_settings().seed_path).fetch(JobQuery())
    unstated = [job for job in raw_jobs
                if job.salary_min is None or job.salary_max is None]
    assert 3 <= len(unstated) <= 5
    assert all(job.salary_min is None and job.salary_max is None for job in unstated)
    fingerprints = [build_job(job).fingerprint for job in raw_jobs]
    assert len(fingerprints) == len(set(fingerprints))


def test_seed_ingest_is_idempotent(session):
    raw_jobs = SeedSource(get_settings().seed_path).fetch(JobQuery())
    first = ingest_raw(session, raw_jobs, embed=False)
    second = ingest_raw(session, raw_jobs, embed=False)
    assert first.inserted == len(raw_jobs)
    assert second.inserted == 0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && pytest tests/test_seed_corpus.py -q`
Expected: FAIL — zero unstated-salary jobs.

- [ ] **Step 3: Add five seed jobs**

Append `demo-101` … `demo-105` with the existing JSON shape (`id`, `source`, `title`,
`company`, `location`, `remote`, `description`, `url`, `currency`, `posted_at`), omitting
`salary_min` and `salary_max`. Use plausible junior/mid titles across at least two role
families and two locations. Make at least two of them strong matches for a junior data
scientist (Python/ML skills, matching title) so they survive retrieval's 40-candidate
cut and appear in the manual check. Do not mention salary in their descriptions.

- [ ] **Step 4: Run the corpus test to verify it passes**

Run: `cd backend && pytest tests/test_seed_corpus.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add data/seed_jobs.json backend/tests/test_seed_corpus.py
git commit -m "chore(data): add seed jobs without salary"
```

---

### Task 7: Update the docs and verify end to end

**Files:**
- Modify: `PROGRESS.md`
- Modify: `docs/superpowers/specs/2026-11-06-retrieval-design.md:52,112`

**Interfaces:** none; this task records the decisions the code now implements.

- [ ] **Step 1: Update PROGRESS.md**

Set "Last done" to M4, "In progress" to none, "Next" to M5. Rewrite invariant 10:

```
10. **M4 returns up to 30 results.** Target 20 salary-known + 10 salary-unstated,
    backfilling unused slots from the other list. Scores blend 0.7 × LLM fit with
    0.3 × retrieval.
```

Add an invariant recording the cache key:

```
11. **Rerank cache keys include the model.** `prompt_version` is
    `rerank-v1@<llm_rerank_model>`; changing the model or prompt must change the string.
```

- [ ] **Step 2: Supersede the M3 notes**

At `docs/superpowers/specs/2026-11-06-retrieval-design.md:52`, change the sentence to
note that M4 returns up to 30 with the flexible split. At line 112, note that M4
partitions the merged pool itself. Do not rewrite the rest of the M3 design.

- [ ] **Step 3: Run the full suite**

Run: `cd backend && pytest -q`
Expected: all tests pass, including the updated API tests; no skips.

- [ ] **Step 4: Re-ingest the demo corpus**

Run: `cd backend && python -m app.cli ingest`
Expected: `"inserted": 5` on the first run after Task 6 (or 0 if already ingested) and
`"embedded": 5` for the new jobs; a second run reports `"inserted": 0, "embedded": 0`.

- [ ] **Step 5: Measure the real first and cached requests**

Start the API from `backend/` with `uvicorn app.main:app --port 8000`, create a small
resume, and call recommendations twice:

```bash
printf 'Priya Sharma\nJunior data scientist. Python, LangChain. 1.5 years.\nBengaluru. Remote ok.\n' > /tmp/m4-verify-resume.txt
RESUME_ID=$(curl -s -X POST -F "file=@/tmp/m4-verify-resume.txt" \
  http://localhost:8000/api/resumes | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -o /tmp/first.json -w 'first: %{time_total}s\n' \
  "http://localhost:8000/api/resumes/$RESUME_ID/recommendations?salary_min=500000"
curl -s -o /tmp/second.json -w 'second: %{time_total}s\n' \
  "http://localhost:8000/api/resumes/$RESUME_ID/recommendations?salary_min=500000"
python3 -c "import json; b=json.load(open('/tmp/second.json')); print(b['rerank_status'], len(b['items']), len(b['items_without_salary']))"
```

Expected: the first call is slower and logs `llm_call ... purpose=rerank` lines with
token counts; the second reuses the cache; `rerank_status` is `ok`; the salary-unstated
list is non-empty because the corpus now has five such jobs. Record both timings in the
commit message.

- [ ] **Step 6: Commit**

```bash
git add PROGRESS.md docs/superpowers/specs/2026-11-06-retrieval-design.md
git commit -m "docs: close M4 rerank and cache"
```

---

## Self-Review Notes

- Spec coverage: token logging (Task 1), rerank core and strict validation (Task 2),
  cache and model-aware versioning (Task 3), blend/partition/selection (Task 4), public
  contract (Task 5), seed data (Task 6), docs and real verification (Task 7).
- Review Focus mapping: wrong id set and string score (Task 2), tie-break (Task 4),
  cross-model cache miss and pool isolation (Task 3), all-known-below-floor and
  unstated-only responses (Tasks 4 and 5).
- Deliberate existing-test changes: default limit 40 → 30 and score meaning are contract
  changes from the approved M4 design, recorded in Task 5. No retrieval service test
  changes.
