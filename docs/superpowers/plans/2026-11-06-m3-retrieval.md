# M3 — Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given a stored resume, filter and rank seed jobs into ~40 deterministic retrieval candidates, with no LLM call.

**Architecture:** A focused `services/retrieval.py` applies SQL filters, computes cosine similarity over stored BGE vectors with numpy, adds a small exact-skill boost, and returns two salary buckets. A thin router exposes it at `GET /api/resumes/{id}/recommendations`; M4 will consume the candidates for LLM reranking.

**Tech Stack:** Python 3.14, FastAPI, SQLModel/SQLite, numpy, fastembed (BGE-small embeddings already stored), pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-retrieval-design.md`

## Global Constraints

- No new dependency: `numpy` and `fastembed` are already installed. No vector database.
- No database schema change. Embeddings stay as SQLite BLOBs scanned in memory.
- No LLM call anywhere in M3, including tests. Tests use fake unit vectors and never load the embedding model.
- Explicit filters are hard. The server never applies resume preferences as hidden filters and never relaxes a filter silently.
- Salary: when `salary_min` is set, jobs with missing or non-comparable salary go to `items_without_salary`; jobs with a known salary below the floor are excluded. When `salary_min` is absent, everything ranks in `items`.
- Ranking: `score = 0.85 × cosine + 0.15 × skill_share`, rounded to 4 decimals; negative cosine clamps to 0.
- `top_k` default is 40 candidates; `limit` is 1–100. The final user-facing 20 is an M4 decision.
- Work on branch `feat/m3-retrieval`; commit locally after each task. Push only at the milestone boundary.
- Conventional Commits, ending with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Run targeted tests with `-q` while iterating; run the full suite once before reporting.

## Review Focus

- A salary floor must not silently drop jobs whose salary is unstated; they belong in `items_without_salary`. Test in Task 4.
- Jobs with no embedding, or with a dimension that differs from the resume vector, must be skipped rather than crash the scan. Test in Task 2.
- `%` and `_` typed into `location` or `role` must be literal characters, not SQL wildcards. Test in Task 3.
- A stored resume with no vector must be embedded, persisted, and usable instead of returning a 500. Test in Task 2.
- Invalid query values (`experience_years=-1`, `salary_min=-1`, `limit=0`, `limit=101`) must return 422, not 500. Test in Task 5.

---

### Task 1: Resume embedding text, re-embed command

**Files:**
- Modify: `backend/app/services/resumes.py:37,52-61`
- Modify: `backend/app/cli.py:15-32`
- Modify: `backend/tests/test_resumes.py`

**Interfaces:**
- Produces: `resume_embed_text(profile: ResumeProfile) -> str` in `app.services.resumes`.
- Produces: `reembed_resumes(session: Session) -> int` in `app.services.resumes`.
- Produces: CLI command `python -m app.cli reembed`, printing `{"reembedded": <int>}`.
- Consumes: `embed_texts`, `to_bytes`, `ResumeProfile`, `Resume`.

- [ ] **Step 0: Commit the approved spec and this plan on the branch**

```bash
cd /Users/bhargavsinguluri/Documents/claude_projects/project_1
git switch feat/m3-retrieval   # created when this plan was approved
git add docs/superpowers/specs/2026-11-06-retrieval-design.md docs/superpowers/plans/2026-11-06-m3-retrieval.md
git commit -m "docs: add M3 retrieval design and plan" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

- [ ] **Step 1: Write the failing embedding-text tests**

Add to `backend/tests/test_resumes.py`:

```python
def test_embedding_text_includes_highlights_and_certifications(session, monkeypatch):
    captured = {}
    profile = make_profile()
    profile.experience[0].highlights.append("Built a RAG pipeline with LangChain")
    profile.certifications.append("AWS Certified Machine Learning")
    profile.preferred_locations = ["Bengaluru", "remote"]

    def fake_embed(texts):
        captured["text"] = texts[0]
        return np.ones((len(texts), 384), dtype=np.float32)

    monkeypatch.setattr(service, "embed_texts", fake_embed)
    monkeypatch.setattr(
        service, "parse_resume_text", lambda text, client=None: (profile, "qwen3:4b")
    )
    service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")

    text = captured["text"]
    assert "RAG pipeline" in text
    assert "AWS Certified Machine Learning" in text
    assert "Bengaluru" in text


def test_reembed_resumes_recomputes_every_stored_vector(session, monkeypatch):
    profile = make_profile()
    monkeypatch.setattr(
        service, "embed_texts", lambda texts: np.ones((len(texts), 384), dtype=np.float32)
    )
    monkeypatch.setattr(
        service, "parse_resume_text", lambda text, client=None: (profile, "qwen3:4b")
    )
    row, _ = service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")

    monkeypatch.setattr(
        service, "embed_texts", lambda texts: np.full((len(texts), 384), 2.0, dtype=np.float32)
    )
    assert service.reembed_resumes(session) == 1
    session.refresh(row)
    assert np.allclose(np.frombuffer(row.embedding, dtype=np.float32), 2.0)
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes.py -q`
Expected: the two new tests FAIL with `AttributeError: module 'app.services.resumes' has no attribute 'reembed_resumes'` and an embedding-text assertion.

- [ ] **Step 3: Implement the embedding text and re-embed function**

In `backend/app/services/resumes.py`:

- Rename `_embed_text` to `resume_embed_text` and use it in `create_resume`.
- The text must include, in this order: summary, target roles, a union of `profile.skills` and `profile.canonical_skills`, preferred locations, experience (`title at company: highlights`), education, certifications, and projects.
- Add:

```python
def reembed_resumes(session: Session) -> int:
    """Recompute and store every resume vector. Skips profiles that fail validation."""
```

Implementation: select all `Resume` rows, validate each `profile` with
`ResumeProfile.model_validate`, skip `ValidationError`, embed `resume_embed_text(profile)`,
store `to_bytes(vector)`, commit once, and return the count embedded.

- [ ] **Step 4: Wire the CLI subcommand**

In `backend/app/cli.py`, add `cmd_reembed` that calls `init_db()`, opens a `Session(engine)`,
calls `reembed_resumes`, and prints `json.dumps({"reembedded": count}, indent=2)`. Register a
`reembed` subparser with the help text `"Recompute stored resume embeddings"`.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes.py -q`
Expected: all tests in the file pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/resumes.py backend/app/cli.py backend/tests/test_resumes.py
git commit -m "feat(backend): embed resume highlights and certifications" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Retrieval core — scoring, ranking, and candidate limits

**Files:**
- Create: `backend/app/services/retrieval.py`
- Modify: `backend/tests/factories.py`
- Create: `backend/tests/test_retrieval.py`

**Interfaces:**
- Produces in `app.services.retrieval`:

```python
SEMANTIC_WEIGHT = 0.85
SKILL_WEIGHT = 0.15
RETRIEVAL_VERSION = "v1"

@dataclass(frozen=True)
class RetrievalFilters:
    location: str | None = None
    remote: bool | None = None
    experience_years: int | None = None
    role: str | None = None
    salary_min: int | None = None

@dataclass(frozen=True)
class Candidate:
    job: Job
    score: float
    matched_skills: list[str]

@dataclass(frozen=True)
class RetrievalResult:
    items: list[Candidate]
    items_without_salary: list[Candidate]
    total: int
    without_salary_total: int

def retrieve_jobs(
    session: Session,
    resume: Resume,
    *,
    filters: RetrievalFilters | None = None,
    limit: int = 40,
) -> RetrievalResult:
```

- Produces: `make_job(**overrides) -> Job` in `tests/factories.py`, with a unique
  `fingerprint` per call. Defaults: title `"AI Engineer"`, company `"Aurora Labs"`,
  location `"Bengaluru, India"`, `remote=False`, `seniority="mid"`,
  `role_family="ai_ml"`, salary `1_200_000`–`1_800_000` INR, skills `["python", "rag"]`,
  `posted_at=datetime(2026, 10, 1, tzinfo=timezone.utc)`.
- Consumes: `from_bytes`, `embed_texts`, `to_bytes`, `resume_embed_text`, `ResumeProfile`,
  `Job`, `Resume`.

- [ ] **Step 1: Add the job factory**

Add `make_job` to `backend/tests/factories.py` as described in Interfaces. It accepts
keyword overrides including `embedding` and returns an unsaved `Job`.

- [ ] **Step 2: Write the failing scoring tests**

Create `backend/tests/test_retrieval.py` with helpers and these tests:

```python
import numpy as np
from datetime import datetime, timezone

from app.embeddings import to_bytes
from app.models import Resume
from app.services.retrieval import retrieve_jobs
from tests.factories import make_job, make_profile


def add_resume(session, *, skills=("python",), vector=(1.0, 0.0), embedded=True):
    profile = make_profile()
    profile.canonical_skills = list(skills)
    row = Resume(
        filename="priya.txt",
        text="Priya Sharma\nPython",
        profile=profile.model_dump(),
        embedding=to_bytes(np.array(vector, dtype=np.float32)) if embedded else None,
        content_hash="resume-hash",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def add_job(session, *, vector=(1.0, 0.0), skills=("python",), **overrides):
    embedding = None if vector is None else to_bytes(np.array(vector, dtype=np.float32))
    job = make_job(embedding=embedding, skills=list(skills), **overrides)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_ranks_by_cosine_similarity(session):
    resume = add_resume(session)
    best = add_job(session, vector=(1.0, 0.0), skills=[])
    worst = add_job(session, vector=(0.0, 1.0), skills=[])
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [best.id, worst.id]
    assert result.items[0].score == 1.0
    assert result.items[1].score == 0.0


def test_skill_overlap_breaks_semantic_ties(session):
    resume = add_resume(session, skills=("python", "rag"))
    overlap = add_job(session, vector=(1.0, 0.0), skills=["python", "rag"])
    miss = add_job(session, vector=(1.0, 0.0), skills=["java"])
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [overlap.id, miss.id]
    assert result.items[0].score == 1.0
    assert result.items[1].score == 0.85


def test_negative_cosine_is_clamped_to_zero(session):
    resume = add_resume(session)
    add_job(session, vector=(-1.0, 0.0), skills=[])
    assert retrieve_jobs(session, resume).items[0].score == 0.0


def test_ties_prefer_newer_postings(session):
    resume = add_resume(session)
    older = add_job(session, posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = add_job(session, posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc))
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [newer.id, older.id]


def test_naive_posted_at_does_not_break_sorting(session):
    resume = add_resume(session)
    add_job(session, posted_at=datetime(2026, 1, 1))
    add_job(session, posted_at=datetime(2026, 2, 1))
    assert len(retrieve_jobs(session, resume).items) == 2


def test_limit_caps_items_but_not_total(session):
    resume = add_resume(session)
    for _ in range(3):
        add_job(session)
    result = retrieve_jobs(session, resume, limit=2)
    assert len(result.items) == 2
    assert result.total == 3
    assert result.items_without_salary == []
    assert result.without_salary_total == 0


def test_jobs_without_embeddings_or_with_wrong_dimensions_are_skipped(session):
    resume = add_resume(session)
    kept = add_job(session)
    add_job(session, vector=None)
    add_job(session, vector=(1.0, 0.0, 0.0))
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [kept.id]
    assert result.total == 1


def test_resume_without_embedding_is_embedded_and_saved(session, monkeypatch):
    resume = add_resume(session, embedded=False)
    job = add_job(session, skills=[])
    monkeypatch.setattr(
        "app.services.retrieval.embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )
    result = retrieve_jobs(session, resume)
    assert result.items[0].job.id == job.id
    session.refresh(resume)
    assert resume.embedding is not None
```

- [ ] **Step 3: Run them and confirm they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: FAIL with `ModuleNotFoundError: app.services.retrieval`.

- [ ] **Step 4: Implement `retrieval.py`**

- `retrieve_jobs` defaults `filters` to `RetrievalFilters()`.
- Load the resume vector from `resume.embedding`; if missing, validate the profile,
  call `embed_texts([resume_embed_text(profile)])[0]`, store `to_bytes`, commit, refresh.
- Select jobs where `Job.embedding.is_not(None)`.
- For each job, `from_bytes(job.embedding)`; skip when its length differs from the resume
  vector.
- `semantic = max(0.0, float(np.dot(job_vector, resume_vector)))`.
- `matched_skills = sorted(set(profile.canonical_skills) & set(job.skills or []))`.
- `skill_share = len(matched_skills) / len(job.skills)` when `job.skills` is non-empty,
  else `0.0`.
- `score = round(SEMANTIC_WEIGHT * semantic + SKILL_WEIGHT * skill_share, 4)`.
- Sort by `(-score, -posted_timestamp, job.id)`; convert naive `posted_at` to UTC and
  treat `None` as negative infinity.
- With no `salary_min`, `items = candidates[:limit]`, the second bucket is empty, and
  `total = len(candidates)`.
- Task 4 adds the salary split.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: `8 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/retrieval.py backend/tests/factories.py backend/tests/test_retrieval.py
git commit -m "feat(backend): rank jobs by embedding similarity and skill overlap" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: Non-salary hard filters

**Files:**
- Modify: `backend/app/services/retrieval.py`
- Modify: `backend/tests/test_retrieval.py`

**Interfaces:**
- Consumes: `RetrievalFilters.location`, `.remote`, `.experience_years`, `.role`.
- Produces: internal `seniority_levels(years: int) -> tuple[str, ...]` and `_like(term: str) -> str`.
- Uses: `infer_role_family` from `app.services.normalize`.

- [ ] **Step 1: Write the failing filter tests**

Append to `backend/tests/test_retrieval.py`:

```python
import pytest

from app.services.retrieval import RetrievalFilters


def test_location_is_a_case_insensitive_substring(session):
    resume = add_resume(session)
    match = add_job(session, location="Bengaluru, India")
    add_job(session, location="Chennai, India")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(location="bengaluru"))
    assert [c.job.id for c in result.items] == [match.id]


def test_location_remote_matches_jobs_flagged_remote(session):
    resume = add_resume(session)
    remote_flag = add_job(session, location="Chennai, India", remote=True)
    remote_text = add_job(session, location="Remote, India", remote=False)
    add_job(session, location="Pune, India", remote=False)
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(location="remote"))
    assert {c.job.id for c in result.items} == {remote_flag.id, remote_text.id}


def test_remote_filter_is_exact(session):
    resume = add_resume(session)
    remote = add_job(session, remote=True)
    add_job(session, remote=False)
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(remote=True))
    assert [c.job.id for c in result.items] == [remote.id]


@pytest.mark.parametrize(
    "years,expected",
    [
        (0, {"intern", "junior"}),
        (1, {"junior", "mid"}),
        (2, {"junior", "mid"}),
        (3, {"mid", "senior"}),
        (5, {"mid", "senior"}),
        (6, {"senior", "lead"}),
    ],
)
def test_experience_maps_to_two_seniority_tiers(session, years, expected):
    resume = add_resume(session)
    for level in ("intern", "junior", "mid", "senior", "lead"):
        add_job(session, seniority=level)
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(experience_years=years)
    )
    assert {c.job.seniority for c in result.items} == expected


def test_role_filter_uses_inferred_family(session):
    resume = add_resume(session)
    ai = add_job(session, title="AI Engineer", role_family="ai_ml")
    add_job(session, title="Data Scientist", role_family="data")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(role="AI Engineer"))
    assert [c.job.id for c in result.items] == [ai.id]


def test_unmapped_role_falls_back_to_title_substring(session):
    resume = add_resume(session)
    widget = add_job(session, title="Widget Wrangler", role_family="other")
    add_job(session, title="Data Scientist", role_family="data")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(role="Widget"))
    assert [c.job.id for c in result.items] == [widget.id]


def test_like_wildcards_are_escaped(session):
    resume = add_resume(session)
    add_job(session, location="Bengaluru, India")
    add_job(session, location="Chennai, India")
    assert retrieve_jobs(
        session, resume, filters=RetrievalFilters(location="%")
    ).items == []
    assert retrieve_jobs(
        session, resume, filters=RetrievalFilters(role="_")
    ).items == []
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: the new filter tests FAIL because filters are not applied.

- [ ] **Step 3: Implement the filters**

- `_like(term)` escapes `\`, `%`, and `_`, then wraps the result in `%...%`.
  All `ilike` calls pass `escape="\\"`.
- `location`: `Job.location.ilike(_like(term), escape="\\")`. When the lowercased term is
  `"remote"`, OR that condition with `Job.remote.is_(True)`.
- `remote`: `Job.remote.is_(filters.remote)`.
- `experience_years`: `Job.seniority.in_(seniority_levels(years))` with the tier mapping
  from the spec.
- `role`: `family = infer_role_family(role)`; when `family != "other"`, filter
  `Job.role_family == family`; otherwise filter `Job.title.ilike(_like(role), escape="\\")`.
- All conditions are ANDed onto the select.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: `20 passed` (8 earlier tests plus 12 filter cases).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retrieval.py backend/tests/test_retrieval.py
git commit -m "feat(backend): filter retrieval by location, remote, experience, and role" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: Salary filter and the two buckets

**Files:**
- Modify: `backend/app/services/retrieval.py`
- Modify: `backend/tests/test_retrieval.py`

**Interfaces:**
- Extends: `retrieve_jobs` fills `RetrievalResult.items_without_salary` and
  `without_salary_total` when `RetrievalFilters.salary_min` is set.
- Consumes: the resume profile's `currency` (default `"INR"` when empty).

- [ ] **Step 1: Write the failing salary tests**

Append to `backend/tests/test_retrieval.py`:

```python
def test_salary_filter_splits_unknown_salaries_into_their_own_bucket(session):
    resume = add_resume(session)
    paid = add_job(session, salary_min=1_200_000, salary_max=1_800_000)
    add_job(session, salary_min=800_000, salary_max=1_000_000)  # below floor
    unknown = add_job(session, salary_min=None, salary_max=None)
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(salary_min=1_500_000)
    )
    assert [c.job.id for c in result.items] == [paid.id]
    assert [c.job.id for c in result.items_without_salary] == [unknown.id]
    assert result.total == 1
    assert result.without_salary_total == 1


def test_different_currency_is_not_comparable(session):
    resume = add_resume(session)
    usd = add_job(session, currency="USD")
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(salary_min=1_000_000)
    )
    assert result.items == []
    assert [c.job.id for c in result.items_without_salary] == [usd.id]


def test_missing_one_salary_bound_counts_as_unknown(session):
    resume = add_resume(session)
    partial = add_job(session, salary_min=1_200_000, salary_max=None)
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(salary_min=1_000_000)
    )
    assert [c.job.id for c in result.items_without_salary] == [partial.id]


def test_salary_limit_applies_to_each_bucket(session):
    resume = add_resume(session)
    for _ in range(3):
        add_job(session, salary_min=1_200_000, salary_max=1_800_000)
    for _ in range(3):
        add_job(session, salary_min=None, salary_max=None)
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(salary_min=1_500_000), limit=1
    )
    assert len(result.items) == 1
    assert len(result.items_without_salary) == 1
    assert result.total == 3
    assert result.without_salary_total == 3


def test_without_salary_filter_everything_ranks_in_items(session):
    resume = add_resume(session)
    add_job(session, salary_min=None, salary_max=None)
    result = retrieve_jobs(session, resume)
    assert len(result.items) == 1
    assert result.items_without_salary == []
    assert result.without_salary_total == 0
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: the new salary tests FAIL because both buckets are not populated.

- [ ] **Step 3: Implement the salary split**

- Validate the resume profile once and read `currency` (`"INR"` when empty).
- When `salary_min` is `None`, keep the current behavior.
- When it is set, for each scored job:
  - missing `salary_min` or `salary_max`, or `job.currency != resume_currency` →
    `items_without_salary`;
  - `job.salary_max >= filters.salary_min` → `items`;
  - otherwise exclude it entirely.
- Sort each bucket with the same key and cap each at `limit`.
- `total = len(paid_bucket)`, `without_salary_total = len(unknown_bucket)` before capping.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_retrieval.py -q`
Expected: `25 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retrieval.py backend/tests/test_retrieval.py
git commit -m "feat(backend): split salary-qualified and unstated jobs in retrieval" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: HTTP endpoint and response models

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/routers/recommendations.py`
- Modify: `backend/app/main.py:8,27-29`
- Create: `backend/tests/test_recommendations_api.py`

**Interfaces:**
- Produces in `app.schemas`:

```python
class RecommendationItem(BaseModel):
    job: JobRead
    score: float
    matched_skills: list[str]

class RecommendationList(BaseModel):
    resume_id: int
    items: list[RecommendationItem]
    items_without_salary: list[RecommendationItem]
    total: int
    without_salary_total: int
    limit: int
    retrieval_version: str
```

- Produces: `GET /api/resumes/{resume_id}/recommendations`.
- Consumes: `retrieve_jobs`, `RetrievalFilters`, `RETRIEVAL_VERSION`, `get_settings`.

- [ ] **Step 1: Write the failing API tests**

Create `backend/tests/test_recommendations_api.py`:

```python
import numpy as np
import pytest

from app.embeddings import to_bytes
from app.models import Resume
from tests.factories import make_job, make_profile


def seed(session, *, job_count=2):
    profile = make_profile()
    resume = Resume(
        filename="priya.txt",
        text="Priya Sharma\nPython",
        profile=profile.model_dump(),
        embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
        content_hash="api-resume-hash",
    )
    session.add(resume)
    session.commit()
    session.refresh(resume)

    jobs = []
    for index in range(job_count):
        job = make_job(
            title=f"AI Engineer {index}",
            embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
            skills=["python"],
        )
        session.add(job)
        jobs.append(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return resume, jobs


def test_returns_ranked_recommendations(api, session):
    resume, jobs = seed(session)
    response = api.get(f"/api/resumes/{resume.id}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume.id
    assert body["retrieval_version"] == "v1"
    assert body["limit"] == 40
    assert body["total"] == 2
    assert body["without_salary_total"] == 0
    assert body["items_without_salary"] == []
    assert {item["job"]["id"] for item in body["items"]} == {job.id for job in jobs}
    assert body["items"][0]["matched_skills"] == ["python"]
    assert "text" not in body["items"][0]["job"]


def test_missing_resume_returns_404(api):
    assert api.get("/api/resumes/9999/recommendations").status_code == 404


def test_limit_is_respected(api, session):
    resume, _ = seed(session, job_count=3)
    body = api.get(f"/api/resumes/{resume.id}/recommendations?limit=1").json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


def test_default_limit_is_the_configured_top_k(api, session):
    resume, _ = seed(session, job_count=41)
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    assert len(body["items"]) == 40
    assert body["total"] == 41


def test_filters_are_passed_through(api, session):
    resume, jobs = seed(session)
    jobs[0].location = "Bengaluru, India"
    jobs[1].location = "Chennai, India"
    session.add(jobs[0])
    session.add(jobs[1])
    session.commit()
    body = api.get(
        f"/api/resumes/{resume.id}/recommendations?location=Bengaluru"
    ).json()
    assert [item["job"]["id"] for item in body["items"]] == [jobs[0].id]


def test_salary_split_is_exposed(api, session):
    resume, _ = seed(session, job_count=1)
    unknown = make_job(
        title="No Salary Role",
        salary_min=None,
        salary_max=None,
        embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
    )
    session.add(unknown)
    session.commit()
    body = api.get(
        f"/api/resumes/{resume.id}/recommendations?salary_min=1500000"
    ).json()
    assert len(body["items"]) == 1
    assert [item["job"]["id"] for item in body["items_without_salary"]] == [unknown.id]


@pytest.mark.parametrize(
    "query",
    ["experience_years=-1", "salary_min=-1", "limit=0", "limit=101"],
)
def test_invalid_query_values_return_422(api, query):
    assert api.get(f"/api/resumes/1/recommendations?{query}").status_code == 422
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_recommendations_api.py -q`
Expected: FAIL with 404 for every route because the endpoint does not exist.

- [ ] **Step 3: Add the response models**

Add `RecommendationItem` and `RecommendationList` to `backend/app/schemas.py` exactly as
in Interfaces.

- [ ] **Step 4: Implement the router**

Create `backend/app/routers/recommendations.py`:

- `GET /resumes/{resume_id}/recommendations`, response model `RecommendationList`.
- Query parameters: `location: str | None`, `remote: bool | None`,
  `experience_years: int | None = Query(None, ge=0, le=60)`,
  `role: str | None`, `salary_min: int | None = Query(None, ge=0)`,
  `limit: int | None = Query(None, ge=1, le=100)`.
- `session.get(Resume, resume_id)`; missing → `HTTPException(404, "Resume not found")`.
- Resolve `limit = limit or get_settings().top_k`.
- Build `RetrievalFilters` and call `retrieve_jobs`.
- Convert each `Candidate` with `JobRead.model_validate(candidate.job)`, and return the
  envelope with `RETRIEVAL_VERSION`.
- Register the router in `main.py` with `prefix="/api", tags=["recommendations"]`.

- [ ] **Step 5: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_recommendations_api.py -q`
Expected: `10 passed` (6 named tests plus 4 invalid-query cases).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/recommendations.py backend/app/main.py backend/tests/test_recommendations_api.py
git commit -m "feat(api): expose resume job recommendations" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: Full verification, re-embed, and milestone close

**Files:**
- Modify: `PROGRESS.md`
- Modify: `README.md` (only if the "How matching works" text is now inaccurate)

**Interfaces:**
- Consumes: the CLI `ingest` and `reembed` commands, the HTTP endpoint.

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: every test passes; the opt-in LLM tests skip.

- [ ] **Step 2: Run ingest and re-embed against the dev database**

Run: `cd backend && .venv/bin/python -m app.cli ingest`
Expected: idempotent JSON stats with no errors.

Run: `cd backend && .venv/bin/python -m app.cli reembed`
Expected: `{"reembedded": <number of stored resumes>}` with no traceback.

- [ ] **Step 3: Exercise the real endpoint**

Start `uvicorn app.main:app --reload` from `backend/`. If the dev database has no resume,
upload the fixture first (the model may fall back to a heuristic profile if Ollama is off):

```bash
curl -s -F "file=@backend/tests/fixtures/sample_resume.pdf" http://localhost:8000/api/resumes > "$CLAUDE_JOB_DIR/tmp/resume.json"
python3 -c "import json,os; print(json.load(open(os.environ['CLAUDE_JOB_DIR'] + '/tmp/resume.json'))['id'])"
```

Then, using that id:

```bash
curl -s "http://localhost:8000/api/resumes/<id>/recommendations?location=Bengaluru&salary_min=1200000&limit=20" | head -c 1200
```

Expected: `200` JSON with `items`, `items_without_salary`, `total`, `limit`, and
`retrieval_version: "v1"`. Sanity-check that the top jobs are plausible for the resume
and that the no-salary bucket is populated only when it should be.

- [ ] **Step 4: Self-review the diff**

Run: `git diff main --stat && git diff main`
Check: no debug prints, no unrelated edits, no secrets, no schema change, no new
dependency, and every new public field name matches the spec.

- [ ] **Step 5: Update `PROGRESS.md`**

Set "Last done" to M3 retrieval, "In progress" to none, and "Next" to M4 rerank + cache.
Add invariants:
- Retrieval is deterministic and LLM-free: explicit hard filters, `0.85 × cosine +
  0.15 × skill`, up to 40 candidates.
- A salary floor never drops jobs with unstated salary; they return in
  `items_without_salary`.
- M4 returns the final 20 results; a vector store waits for the Postgres + pgvector
  migration.

Keep the file under ~60 lines.

- [ ] **Step 6: Commit the milestone**

```bash
git add PROGRESS.md README.md
git commit -m "docs: close M3 retrieval" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

Do not push until the full suite and the real-endpoint check both pass.
