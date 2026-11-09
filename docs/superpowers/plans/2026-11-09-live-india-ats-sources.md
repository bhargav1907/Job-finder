# Live India ATS Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch real Indian job postings from public employer ATS boards (Greenhouse, Keka, Darwinbox) into FLA Job Finder through the existing `JobSource` protocol.

**Architecture:** A committed `data/boards.json` catalogue lists validated `(provider, board, company)` rows. One adapter per provider maps that provider's public board API into `RawJob`, sharing only mapping helpers and an HTTP client factory. `python -m app.cli ingest --live` builds all configured sources, ingests them with the existing service, and never runs during a request. Ingest identity moves to `(source, external_id)` so an edited posting is not re-inserted.

**Tech Stack:** Python 3.14, httpx (already a dependency), SQLModel/SQLite, pytest with `httpx.MockTransport`.

**Spec:** `docs/research/india-ats-probe-2026-11-09.md`

## Global Constraints

- No new dependencies. `httpx` is already in `backend/requirements.txt`.
- All ingestion goes through `app/sources/base.py`; routers never call a provider.
- Live fetching is CLI-only (`python -m app.cli ingest --live`). The API never fetches at request time.
- Only public ATS board APIs. Never scrape LinkedIn, Indeed, or Naukri.
- No database schema changes in this milestone. Posting lifecycle (`last_seen_at`, `closed_at`) is deferred until Bhargav approves a schema change.
- Live adapters fetch each configured board in full and ignore `JobQuery` filters; ranking filters happen later.
- Salary is not parsed from live feeds in this milestone. `salary_min` / `salary_max` stay `None` unless the provider supplies an unambiguous, already-normalized value. Never guess a currency or period.
- Every commit is Conventional Commits. Do not push.
- Never delete, skip, weaken, or rewrite a test to get green.

## Review Focus

1. **One board fails (404, timeout, malformed JSON):** the other boards still ingest and the run exits successfully. Pinned in Tasks 3–5.
2. **A posting is missing `id` or `title`:** it is skipped, not an exception. Pinned in Tasks 3–5.
3. **A posting is edited upstream (same id, new title):** re-ingest does not insert a duplicate. Pinned in Task 6.
4. **Darwinbox pagination never empties or declares a different total:** the walk is bounded and only that board is rejected. Pinned in Task 5.
5. **A live posting has no salary:** it is stored as unstated (`None`), never 0 and never a guessed currency/period. Pinned in Tasks 3–5.

---

### Task 1: Board catalogue and loader

**Files:**
- Create: `data/boards.json`
- Create: `backend/app/sources/boards.py`
- Modify: `backend/app/config.py` (add `boards_path`)
- Test: `backend/tests/test_boards.py`

**Interfaces:**
- Produces: `Board(provider: str, board: str, company: str)` frozen dataclass; `BoardConfigError(ValueError)`; `load_boards(path: str | Path) -> list[Board]`.
- Produces: `Settings.boards_path: Path` defaulting to `PROJECT_ROOT / "data" / "boards.json"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_boards.py
import json
from pathlib import Path

import pytest

from app.config import PROJECT_ROOT
from app.sources.boards import Board, BoardConfigError, load_boards


def write(tmp_path, rows):
    path = tmp_path / "boards.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_load_boards_reads_provider_board_company(tmp_path):
    path = write(tmp_path, [{"provider": "keka", "board": "softobiz", "company": "Softobiz"}])
    assert load_boards(path) == [Board("keka", "softobiz", "Softobiz")]


def test_load_boards_rejects_unknown_provider(tmp_path):
    path = write(tmp_path, [{"provider": "naukri", "board": "x", "company": "X"}])
    with pytest.raises(BoardConfigError, match="unknown provider"):
        load_boards(path)


def test_load_boards_rejects_bad_darwinbox_host(tmp_path):
    path = write(tmp_path, [{"provider": "darwinbox", "board": "evil.com/x", "company": "X"}])
    with pytest.raises(BoardConfigError, match="darwinbox host"):
        load_boards(path)


def test_load_boards_rejects_duplicate_provider_board(tmp_path):
    row = {"provider": "greenhouse", "board": "quince", "company": "Quince"}
    path = write(tmp_path, [row, row])
    with pytest.raises(BoardConfigError, match="duplicate"):
        load_boards(path)


def test_committed_board_file_is_valid():
    boards = load_boards(PROJECT_ROOT / "data" / "boards.json")
    assert {board.provider for board in boards} == {"darwinbox", "greenhouse", "keka"}
    assert len(boards) >= 18
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_boards.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.boards'`.

- [ ] **Step 3: Implement the catalogue**

`data/boards.json` starts with the 18 boards validated on 2026-11-09:

```json
[
  {"provider": "greenhouse", "board": "quince", "company": "Quince"},
  {"provider": "greenhouse", "board": "razorpaysoftwareprivatelimited", "company": "Razorpay"},
  {"provider": "greenhouse", "board": "agoda", "company": "Agoda"},
  {"provider": "greenhouse", "board": "blackduck", "company": "Black Duck Software"},
  {"provider": "greenhouse", "board": "spacexglobal", "company": "SpaceX"},
  {"provider": "greenhouse", "board": "pointwild", "company": "Point Wild"},
  {"provider": "greenhouse", "board": "emergenceai", "company": "Emergence AI"},
  {"provider": "keka", "board": "softobiz", "company": "Softobiz Technologies"},
  {"provider": "keka", "board": "mosaicwellness", "company": "Mosaic Wellness"},
  {"provider": "keka", "board": "eyerov", "company": "IROV"},
  {"provider": "darwinbox", "board": "pwc.darwinbox.com", "company": "PwC India"},
  {"provider": "darwinbox", "board": "autalenthub.darwinbox.in", "company": "AU Small Finance Bank"},
  {"provider": "darwinbox", "board": "kotaklifeinsurance.darwinbox.in", "company": "Kotak Life Insurance"},
  {"provider": "darwinbox", "board": "paplconnectplus.darwinbox.in", "company": "PAPL"},
  {"provider": "darwinbox", "board": "nectar.darwinbox.in", "company": "Mahindra Logistics"},
  {"provider": "darwinbox", "board": "oneeverest.darwinbox.in", "company": "Everest Industries"},
  {"provider": "darwinbox", "board": "dbx.darwinbox.in", "company": "Darwinbox Digital"},
  {"provider": "darwinbox", "board": "geppeoplecentral.darwinbox.com", "company": "GEP Worldwide"}
]
```

In `boards.py`, validate the top-level list, non-empty string fields, known providers, provider-specific board shapes, and `(provider, board)` uniqueness. Use these exact patterns:

```python
_BOARD_PATTERNS = {
    "greenhouse": re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
    "keka": re.compile(r"^[a-z0-9][a-z0-9-]*$"),
    "darwinbox": re.compile(r"^[a-z0-9][a-z0-9-]*\.darwinbox\.(?:in|com)$"),
}
```

Add `boards_path: Path = PROJECT_ROOT / "data" / "boards.json"` under the Storage section of `Settings`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_boards.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add data/boards.json backend/app/sources/boards.py backend/app/config.py backend/tests/test_boards.py
git commit -m "feat(sources): add validated ATS board catalogue"
```

---

### Task 2: Provider-neutral mapping helpers

**Files:**
- Create: `backend/app/sources/mapping.py`
- Test: `backend/tests/test_source_mapping.py`

**Interfaces:**
- Produces: `html_to_text(value: str, unescape_times: int = 1) -> str`
- Produces: `parse_iso_datetime(value: str | None) -> datetime | None` (always timezone-aware UTC)
- Produces: `parse_epoch_seconds(value: int | None) -> datetime | None`
- Produces: `join_nonempty(*parts: str) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_source_mapping.py
from datetime import datetime, timezone

from app.sources.mapping import (
    html_to_text,
    join_nonempty,
    parse_epoch_seconds,
    parse_iso_datetime,
)


def test_html_to_text_unwraps_entities_and_block_tags():
    assert html_to_text("<p>Hello &amp; welcome</p><p>Second<br>line</p>") == (
        "Hello & welcome\nSecond\nline"
    )


def test_html_to_text_drops_script_and_style():
    assert html_to_text("<style>.x{}</style><script>alert(1)</script><b>Build</b> things") == (
        "Build things"
    )


def test_html_to_text_can_decode_twice_encoded_markup():
    assert html_to_text("&amp;lt;p&amp;gt;Hi&amp;lt;/p&amp;gt;", unescape_times=2) == "Hi"


def test_parse_iso_datetime_normalizes_to_utc():
    assert parse_iso_datetime("2026-10-01T10:00:00Z") == datetime(
        2026, 10, 1, 10, tzinfo=timezone.utc
    )
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime(None) is None


def test_parse_epoch_seconds():
    assert parse_epoch_seconds(1790812800) == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert parse_epoch_seconds(None) is None


def test_join_nonempty_skips_blank_parts():
    assert join_nonempty("Mumbai", "", "India") == "Mumbai, India"
    assert join_nonempty("", "  ", "") == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_source_mapping.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.mapping'`.

- [ ] **Step 3: Implement the helpers**

`html_to_text` uses `html.unescape` `unescape_times` times, then an `HTMLParser` subclass that: skips `script`/`style` contents, emits `\n` for block tags (`p`, `div`, `li`, `tr`, `h1`–`h6`, `br`), emits a space for inline tags, and finally collapses any whitespace run containing a newline to a single `\n` and every other whitespace run to one space. Trim the result.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_source_mapping.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/sources/mapping.py backend/tests/test_source_mapping.py
git commit -m "feat(sources): add provider-neutral mapping helpers"
```

---

### Task 3: Shared HTTP client and Greenhouse adapter

**Files:**
- Create: `backend/app/sources/http.py`
- Create: `backend/app/sources/greenhouse.py`
- Test: `backend/tests/test_greenhouse.py`

**Interfaces:**
- Produces: `default_client() -> httpx.Client` (20 s timeout, one retry, `follow_redirects=True`, UA `FLAJobFinder/0.1 (internal demo)`).
- Produces: `client_scope(client: httpx.Client | None)` context manager that yields the injected client or a temporary default client without closing an injected one.
- Produces: `GreenhouseSource(boards: Sequence[Board], client: httpx.Client | None = None)` with `name = "greenhouse"`, `boards: tuple[Board, ...]`, and `fetch(query: JobQuery) -> list[RawJob]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_greenhouse.py
import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.greenhouse import GreenhouseSource

PAYLOAD = {
    "jobs": [
        {
            "id": 42,
            "title": "Senior AI Engineer",
            "absolute_url": "https://boards.greenhouse.io/quince/jobs/42",
            "updated_at": "2026-10-01T10:00:00Z",
            "content": "&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;",
            "location": {"name": "Bengaluru, India"},
        }
    ]
}


def test_fetch_maps_a_greenhouse_posting():
    def handler(request):
        assert request.url.params["content"] == "true"
        assert request.url.params["pay_transparency"] == "true"
        return httpx.Response(200, json=PAYLOAD)

    source = GreenhouseSource(
        [Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    jobs = source.fetch(JobQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "greenhouse"
    assert job.external_id == "42"
    assert job.title == "Senior AI Engineer"
    assert job.company == "Quince"
    assert job.location == "Bengaluru, India"
    assert job.description == "Build & ship"
    assert job.url == "https://boards.greenhouse.io/quince/jobs/42"
    assert job.salary_min is None and job.salary_max is None


def test_one_failing_board_does_not_stop_the_others():
    def handler(request):
        if "/broken/" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=PAYLOAD)

    source = GreenhouseSource(
        [Board("greenhouse", "broken", "Broken"), Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert [job.company for job in source.fetch(JobQuery())] == ["Quince"]


def test_posting_without_id_or_title_is_skipped():
    payload = {"jobs": [{"id": 1, "title": "", "location": {"name": ""}}, {"title": "No id"}]}
    source = GreenhouseSource(
        [Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))),
    )
    assert source.fetch(JobQuery()) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_greenhouse.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.http'`.

- [ ] **Step 3: Implement the client and adapter**

Greenhouse endpoint: `GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs` with `content=true&pay_transparency=true`.

Mapping rules:
- `external_id = str(row["id"])`; skip when id or title is blank.
- `company = board.company`.
- `location = row.get("location", {}).get("name") or ""`.
- `description = html_to_text(row.get("content") or "")`.
- `url = row.get("absolute_url") or ""`.
- `posted_at = parse_iso_datetime(row.get("updated_at"))`.
- `salary_min`, `salary_max` stay `None`; `currency` stays the `RawJob` default.
- A non-list `jobs` value raises `SourceError`; `fetch` logs a warning per failed board and continues. Add `SourceError(RuntimeError)` to `backend/app/sources/base.py`.

Catch only `httpx.HTTPError`, `SourceError`, `ValueError`, and `KeyError` per board.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_greenhouse.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/sources/http.py backend/app/sources/greenhouse.py backend/app/sources/base.py backend/tests/test_greenhouse.py
git commit -m "feat(sources): add Greenhouse board adapter"
```

---

### Task 4: Keka adapter

**Files:**
- Create: `backend/app/sources/keka.py`
- Test: `backend/tests/test_keka.py`

**Interfaces:**
- Produces: `KekaSource(boards: Sequence[Board], client: httpx.Client | None = None)` with `name = "keka"`, `boards: tuple[Board, ...]`, and `fetch(query: JobQuery) -> list[RawJob]`.
- Consumes: `client_scope`, `html_to_text`, `join_nonempty`, `parse_iso_datetime`, `SourceError`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_keka.py
import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.keka import KekaSource

PAYLOAD = [
    {
        "id": 7,
        "title": "Backend Developer",
        "description": "<p>Python &amp; SQL</p>",
        "jobType": 2,
        "publishedOn": "2026-10-02T08:30:00Z",
        "jobLocations": [{"city": "Pune", "state": "Maharashtra", "countryName": "India"}],
    }
]


def test_fetch_maps_a_keka_posting():
    def handler(request):
        assert str(request.url) == "https://softobiz.keka.com/careers/api/jobs/default/active"
        return httpx.Response(200, json=PAYLOAD)

    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    job = source.fetch(JobQuery())[0]

    assert job.source == "keka"
    assert job.external_id == "7"
    assert job.title == "Backend Developer"
    assert job.company == "Softobiz"
    assert job.location == "Pune, Maharashtra, India"
    assert job.description == "Python & SQL"
    assert job.url == "https://softobiz.keka.com/careers/jobdetails/7"
    assert job.salary_min is None and job.salary_max is None


def test_malformed_keka_board_is_skipped():
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"oops": True}))),
    )
    assert source.fetch(JobQuery()) == []


def test_keka_posting_without_title_is_skipped():
    payload = [{"id": 8, "title": "", "jobLocations": []}]
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))),
    )
    assert source.fetch(JobQuery()) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_keka.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.keka'`.

- [ ] **Step 3: Implement the adapter**

Keka endpoint: `GET https://{board}.keka.com/careers/api/jobs/default/active`. The response is a bare JSON list; anything else raises `SourceError`.

Mapping rules:
- `external_id = str(row["id"])`; skip when id or title is blank.
- `company = board.company`. Do not make the extra `careerportalinfo` request.
- `location = join_nonempty(city, state, countryName)` from the first `jobLocations` entry.
- `description = html_to_text(row.get("description") or "")`.
- `url = f"https://{board.board}.keka.com/careers/jobdetails/{external_id}"`.
- `remote = "remote" in location.lower() or "remote" in title.lower()`.
- `posted_at = parse_iso_datetime(row.get("publishedOn"))`.
- Salary fields stay `None`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_keka.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/sources/keka.py backend/tests/test_keka.py
git commit -m "feat(sources): add Keka board adapter"
```

---

### Task 5: Darwinbox adapter

**Files:**
- Create: `backend/app/sources/darwinbox.py`
- Test: `backend/tests/test_darwinbox.py`

**Interfaces:**
- Produces: `DarwinboxSource(boards: Sequence[Board], client: httpx.Client | None = None)` with `name = "darwinbox"`, `boards: tuple[Board, ...]`, and `fetch(query: JobQuery) -> list[RawJob]`.
- Consumes: `client_scope`, `html_to_text`, `parse_epoch_seconds`, `normalize_ws` from `app.services.normalize`, `SourceError`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_darwinbox.py
import json

import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.darwinbox import DarwinboxSource


def page(rows, total):
    return {"status": "success", "data": rows, "job_counts": total}


ROW = {
    "id": "db-1",
    "title": " Data Analyst ",
    "jd": "&amp;lt;p&amp;gt;SQL and dashboards&amp;lt;/p&amp;gt;",
    "country": "India",
    "officelocations_without_area": ["Mumbai, Maharashtra\r, India"],
    "is_remote": 0,
    "posted_on": 1790812800,
}


def test_fetch_maps_darwinbox_posting_and_pages():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["page"])
        if body["page"] == 1:
            return httpx.Response(200, json=page([ROW], 1))
        return httpx.Response(200, json=page([], 1))

    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    jobs = source.fetch(JobQuery())

    assert calls == [1, 2]
    job = jobs[0]
    assert job.source == "darwinbox"
    assert job.external_id == "db-1"
    assert job.title == "Data Analyst"
    assert job.company == "PwC India"
    assert job.location == "Mumbai, Maharashtra, India"
    assert job.description == "SQL and dashboards"
    assert job.url == "https://pwc.darwinbox.com/ms/candidatev2/main/careers/jobDetails/db-1"
    assert job.salary_min is None


def test_count_mismatch_rejects_only_that_board():
    def handler(request):
        board = request.url.host.split(".")[0]
        if board == "broken":
            return httpx.Response(200, json=page([], 99))
        return httpx.Response(200, json=page([ROW], 1))

    source = DarwinboxSource(
        [Board("darwinbox", "broken.darwinbox.com", "Broken"),
         Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert [job.company for job in source.fetch(JobQuery())] == ["PwC India"]


def test_bad_host_makes_no_request():
    def handler(request):
        raise AssertionError("must not call the network")

    source = DarwinboxSource(
        [Board("darwinbox", "evil.example.com", "Evil")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert source.fetch(JobQuery()) == []


def test_posting_without_title_is_skipped():
    payload = page([{"id": "x", "title": "  "}], 1)
    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))),
    )
    assert source.fetch(JobQuery()) == []


def test_endless_pagination_is_bounded():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["page"])
        row = dict(ROW, id=f"db-{body['page']}")
        return httpx.Response(200, json=page([row], 999_999))

    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert source.fetch(JobQuery()) == []
    assert len(calls) == 50
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_darwinbox.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.darwinbox'`.

- [ ] **Step 3: Implement the adapter**

Endpoint: `POST https://{board}/ms/candidateapi/job/alljobs` with `{"page": page, "limit": 100}`.

Rules:
- Validate the host against `^[a-z0-9][a-z0-9-]*\.darwinbox\.(?:in|com)$` before any request; a bad host raises `SourceError` inside the per-board try block.
- Require `status == "success"` and an integer `job_counts`, else `SourceError`.
- Page from 1 until `data` is empty; stop with `SourceError` after 50 pages (5,000 postings).
- Deduplicate by posting id, then require the gathered count to equal the first page's `job_counts`; a mismatch raises `SourceError`.
- Skip rows with blank id or title.
- `location = normalize_ws(first location.replace("\r", ""))`.
- `description`: if `html_to_text(jd, unescape_times=1)` still starts with `&lt;` or contains `&amp;lt;`, use `unescape_times=2`; otherwise use the once-decoded text. This covers the once- and twice-encoded bodies measured in the probe.
- `remote = row.get("is_remote") == 1 or "remote" in location.lower() or "remote" in title.lower()`.
- `posted_at = parse_epoch_seconds(row.get("posted_on"))`.
- `url = f"https://{board}/ms/candidatev2/main/careers/jobDetails/{external_id}"`.
- Salary fields stay `None`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_darwinbox.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/sources/darwinbox.py backend/tests/test_darwinbox.py
git commit -m "feat(sources): add Darwinbox board adapter"
```

---

### Task 6: Idempotent ingest by provider identity

**Files:**
- Modify: `backend/app/services/ingest.py:41-65`
- Test: `backend/tests/test_ingest.py` (create)

**Interfaces:**
- Consumes: `ingest_raw(session: Session, raw_jobs: list[RawJob], embed: bool = True) -> IngestResult`.
- Produces: no signature change. Behaviour: an existing `(source, external_id)` pair is skipped before the fingerprint check; blank `external_id` falls back to fingerprint only.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_ingest.py
from app.services.ingest import ingest_raw
from app.sources.base import RawJob


def raw(**overrides):
    data = {
        "source": "greenhouse",
        "external_id": "42",
        "title": "AI Engineer",
        "company": "Quince",
        "location": "Bengaluru, India",
        "url": "https://boards.greenhouse.io/quince/jobs/42",
    }
    data.update(overrides)
    return RawJob(**data)


def test_same_source_and_external_id_is_not_reinserted_after_a_title_edit(session):
    first = ingest_raw(session, [raw()], embed=False)
    second = ingest_raw(session, [raw(title="Senior AI Engineer")], embed=False)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped == 1


def test_same_job_from_two_sources_is_deduped_by_fingerprint(session):
    first = ingest_raw(session, [raw(source="greenhouse", external_id="1")], embed=False)
    second = ingest_raw(session, [raw(source="keka", external_id="2")], embed=False)
    assert first.inserted == 1
    assert second.inserted == 0


def test_blank_external_id_still_dedupes_by_fingerprint(session):
    first = ingest_raw(session, [raw(source="custom", external_id="")], embed=False)
    second = ingest_raw(session, [raw(source="custom", external_id="")], embed=False)
    assert first.inserted == 1
    assert second.skipped == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_ingest.py -q`
Expected: `test_same_source_and_external_id_is_not_reinserted_after_a_title_edit` FAILS with `assert 1 == 0` on `second.inserted`.

- [ ] **Step 3: Implement the identity check**

Inside the loop, after the in-batch `seen` check and before the fingerprint query:

```python
if job.external_id:
    existing = session.exec(
        select(Job).where(Job.source == job.source, Job.external_id == job.external_id)
    ).first()
    if existing:
        result.skipped += 1
        continue
```

Do not update the existing row in this milestone; ranking reads the first-seen snapshot.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_ingest.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ingest.py backend/tests/test_ingest.py
git commit -m "fix(ingest): dedupe live postings by source and external id"
```

---

### Task 7: Live ingest CLI

**Files:**
- Create: `backend/app/sources/registry.py`
- Modify: `backend/app/cli.py`
- Test: `backend/tests/test_cli_live.py` (create)

**Interfaces:**
- Produces: `build_sources(boards: Sequence[Board]) -> list[JobSource]` returning one adapter per provider that has at least one board.
- Produces: CLI `python -m app.cli ingest --live [--boards PATH] [--no-embed]`. Without `--live`, behaviour is unchanged (seed corpus).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_cli_live.py
from app.cli import build_parser
from app.sources.boards import Board
from app.sources.darwinbox import DarwinboxSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.keka import KekaSource
from app.sources.registry import build_sources


def test_build_sources_groups_by_provider():
    boards = [
        Board("greenhouse", "quince", "Quince"),
        Board("keka", "softobiz", "Softobiz"),
        Board("darwinbox", "pwc.darwinbox.com", "PwC India"),
    ]
    sources = build_sources(boards)
    assert [type(source) for source in sources] == [
        GreenhouseSource,
        KekaSource,
        DarwinboxSource,
    ]
    assert [len(source.boards) for source in sources] == [1, 1, 1]


def test_ingest_defaults_to_seed_and_accepts_live():
    parser = build_parser()
    assert parser.parse_args(["ingest"]).live is False
    args = parser.parse_args(["ingest", "--live", "--no-embed"])
    assert args.live is True and args.no_embed is True
```

Expose the configured boards as `source.boards` (a tuple) on each adapter for this test.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_cli_live.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sources.registry'` and `unrecognized arguments: --live`.

- [ ] **Step 3: Implement the registry and CLI path**

`registry.py` maps `{"greenhouse": GreenhouseSource, "keka": KekaSource, "darwinbox": DarwinboxSource}` and emits sources in that insertion order, passing each provider's boards in catalogue order and skipping providers with no boards.

In `cmd_ingest`:

```python
if args.live:
    sources = build_sources(load_boards(args.boards or settings.boards_path))
    raw_jobs = [job for source in sources for job in source.fetch(JobQuery())]
else:
    raw_jobs = SeedSource(settings.seed_path).fetch(JobQuery())
```

Add `--live` (`store_true`) and `--boards` (`type=Path`, default `None`). Keep the existing `--no-embed`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_cli_live.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/sources/registry.py backend/app/cli.py backend/tests/test_cli_live.py
git commit -m "feat(cli): ingest live ATS boards with --live"
```

---

### Task 8: Documentation and full verification

**Files:**
- Modify: `PROGRESS.md`
- Modify: `CLAUDE.md` (commands section only)
- Test: full suite

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: Update `PROGRESS.md`**

Set "Last done" to M4.5 — live ATS sources; add invariants:
- `data/boards.json` is the only list of live boards; an adapter never invents a host.
- Live ingest is CLI-only; the API never fetches at request time.
- Jobs are identified by `(source, external_id)`; fingerprint dedupes across sources.
- No `last_seen_at` / `closed_at` until a schema change is approved.
- Salary from live boards stays unstated; do not guess currency or period.

Set "Next" to SmartRecruiters + Freshteam adapters and an India-only board filter.

- [ ] **Step 2: Add the live command to `CLAUDE.md`**

Under Backend commands, add:

```
- `python -m app.cli ingest --live` — fetch live ATS boards from `data/boards.json`
```

- [ ] **Step 3: Run the targeted tests**

Run: `cd backend && pytest tests/test_boards.py tests/test_source_mapping.py tests/test_greenhouse.py tests/test_keka.py tests/test_darwinbox.py tests/test_ingest.py tests/test_cli_live.py -q`
Expected: all pass.

- [ ] **Step 4: Run the full backend suite**

Run: `cd backend && pytest -q`
Expected: all pass, no failures.

- [ ] **Step 5: Run a live smoke test without touching the demo DB**

Run from `backend/`, pointing the database at a throwaway file so the demo DB is untouched:

```bash
DATABASE_URL="sqlite:///$CLAUDE_JOB_DIR/tmp/live_smoke.db" \
  python -m app.cli ingest --live --boards ../data/boards.json --no-embed
```

Expected: JSON with `"fetched"` greater than 0. If a board is down, the run still completes; report which provider returned zero. Delete the throwaway DB afterwards.

- [ ] **Step 6: Self-review and commit**

Run: `git diff` and `git status`.
Expected: only the files above; no debug prints, no secrets, no unrelated edits.

```bash
git add PROGRESS.md CLAUDE.md
git commit -m "docs: record live ATS source milestone"
```
