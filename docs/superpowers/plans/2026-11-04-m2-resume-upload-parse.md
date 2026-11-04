# M2 — Resume Upload and Parse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept a PDF/DOCX/TXT resume, extract its text locally, parse a validated full ATS profile with Qwen3 4B, and store it in SQLite with deduplication and embeddings.

**Architecture:** One schema-constrained LLM call per new resume, then deterministic reconciliation of salary and canonical skills. Text extraction, parsing, and persistence live in three focused service modules behind a thin router. Identical text never reaches the model twice.

**Tech Stack:** Python 3.14, FastAPI, SQLModel/SQLite, pypdf, python-docx, Ollama (`qwen3:4b`), fastembed, pytest.

**Spec:** `docs/superpowers/specs/2026-11-04-resume-upload-parse-design.md`

## Global Constraints

- Local models only: parse `qwen3:4b`, fallback `llama3.2:3b`, rerank stays `lfm3:1.7b`. Never a hosted/coding-plan endpoint.
- No database schema change: use the existing `resumes` table (`filename, text, profile, embedding, content_hash, parse_model, created_at`).
- No raw upload retained; never log resume text; never return resume text from the API.
- Max upload 5 MiB (`5 * 1024 * 1024`); max extracted text 50,000 chars.
- One new dependency: `python-docx==1.2.0`.
- Every commit uses Conventional Commits and ends with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Run targeted tests with `-q` while iterating; run the full suite once before reporting.
- Work on branch `feat/m2-resume-parse`; commit locally at each task. Push only after the milestone is verified.

## Review Focus

- A monthly stipend ("₹25,000–35,000 per month") must be annualized, not stored as an annual ₹25k. Test in Task 4.
- A scanned/image-only or corrupt PDF must return 422, never 500. Test in Tasks 2 and 7.
- DOCX content that lives only in tables must be extracted, not silently dropped. Test in Task 2.
- A very long resume must be capped at 50,000 chars so the model context and memory stay bounded. Test in Task 2.
- An uppercase extension (`.PDF`) must be accepted. Test in Tasks 2 and 7.

---

### Task 1: Branch, test harness, and settings

**Files:**
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_settings.py`
- Modify: `backend/app/config.py:24-39`

**Interfaces:**
- Produces: `Settings.llm_parse_model == "qwen3:4b"`, `Settings.llm_num_ctx == 8192`, `Settings.resume_max_bytes == 5_242_880`, `Settings.resume_max_chars == 50_000`.
- Produces: pytest fixtures `engine`, `session`, and `api` in `tests/conftest.py`.

- [ ] **Step 0: Create the branch**

```bash
cd /Users/bhargavsinguluri/Documents/claude_projects/project_1
git switch -c feat/m2-resume-parse
git add docs/superpowers
git commit -m "docs: add M2 resume upload and parse design and plan" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

- [ ] **Step 1: Write the failing settings test**

```python
# backend/tests/test_settings.py
from app.config import get_settings


def test_parse_and_resume_defaults():
    settings = get_settings()
    assert settings.llm_parse_model == "qwen3:4b"
    assert settings.llm_rerank_model == "lfm3:1.7b"
    assert settings.llm_fallback_model == "llama3.2:3b"
    assert settings.llm_num_ctx == 8192
    assert settings.resume_max_bytes == 5 * 1024 * 1024
    assert settings.resume_max_chars == 50_000
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_settings.py -q`
Expected: FAIL with `AttributeError` or an assertion on an existing default.

- [ ] **Step 3: Add the settings**

In `backend/app/config.py`, change `llm_parse_model` to `"qwen3:4b"` and add:

```python
    llm_num_ctx: int = 8192
    resume_max_bytes: int = 5 * 1024 * 1024
    resume_max_chars: int = 50_000
```

- [ ] **Step 4: Add `pytest.ini` and `conftest.py`**

```ini
# backend/pytest.ini
[pytest]
pythonpath = .
testpaths = tests
```

```python
# backend/tests/conftest.py
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401 - registers tables
from app.db import get_session
from app.main import app


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture
def session(engine) -> Iterator[Session]:
    with Session(engine) as db:
        yield db


@pytest.fixture
def api(session, monkeypatch):
    monkeypatch.setattr("app.main.init_db", lambda: None)

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

Also create an empty `backend/tests/__init__.py`.

- [ ] **Step 5: Run the test and confirm it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_settings.py -q`
Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/pytest.ini backend/tests backend/app/config.py
git commit -m "test(backend): add pytest harness and M2 settings" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Text extraction from PDF, DOCX, and TXT

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/services/resume_text.py`
- Create: `backend/tests/test_resume_text.py`
- Create: `backend/tests/fixtures/sample_resume.pdf`

**Interfaces:**
- Produces: `extract_text(filename: str, data: bytes, *, max_chars: int = 50_000) -> str`
- Produces: exceptions `UnsupportedFormat(ValueError)` and `EmptyResume(ValueError)`
- Produces: `SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})`

- [ ] **Step 1: Add the dependency**

Append `python-docx==1.2.0` to `backend/requirements.txt`, then run:

```bash
cd backend && .venv/bin/pip install python-docx==1.2.0
```

- [ ] **Step 2: Create the PDF fixture**

Generate a small one-page PDF whose text includes `Priya Sharma`:

```bash
mkdir -p backend/tests/fixtures
printf 'Priya Sharma\nPython, SQL, pandas\n' > /Users/bhargavsinguluri/.claude/jobs/acf9dadb/tmp/fixture.txt
/usr/sbin/cupsfilter -m application/pdf /Users/bhargavsinguluri/.claude/jobs/acf9dadb/tmp/fixture.txt > backend/tests/fixtures/sample_resume.pdf
```

If `cupsfilter` is unavailable, create the fixture with a minimal hand-written PDF whose text stream contains `(Priya Sharma) Tj`; it must parse with `pypdf.PdfReader`.

- [ ] **Step 3: Write the failing extraction tests**

```python
# backend/tests/test_resume_text.py
import io
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from app.services.resume_text import EmptyResume, UnsupportedFormat, extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extracts_utf8_txt():
    text = extract_text("resume.txt", "Priya Sharma\nPython, SQL".encode())
    assert "Priya Sharma" in text
    assert "Python, SQL" in text


def test_falls_back_to_latin1():
    assert "Café" in extract_text("resume.txt", "Café\nPython".encode("latin-1"))


def test_normalizes_whitespace():
    text = extract_text("resume.txt", b"Priya   Sharma\n\n\n\nPython\tSQL")
    assert "Priya Sharma" in text
    assert "\n\n\n" not in text


def test_caps_long_text():
    text = extract_text("resume.txt", b"x" * 60_000, max_chars=1_000)
    assert len(text) <= 1_000


def test_uppercase_pdf_suffix_is_supported():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    assert "Priya Sharma" in extract_text("Resume.PDF", data)


def test_extracts_pdf_text():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    assert "Priya Sharma" in extract_text("resume.pdf", data)


def test_pdf_without_text_raises_empty():
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    with pytest.raises(EmptyResume):
        extract_text("blank.pdf", buffer.getvalue())


def test_corrupt_pdf_raises_empty():
    with pytest.raises(EmptyResume):
        extract_text("bad.pdf", b"not a pdf")


def test_extracts_docx_paragraphs_and_tables():
    document = Document()
    document.add_paragraph("Priya Sharma")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Python"
    table.cell(0, 1).text = "SQL"
    buffer = io.BytesIO()
    document.save(buffer)
    text = extract_text("resume.docx", buffer.getvalue())
    assert "Priya Sharma" in text
    assert "Python" in text and "SQL" in text


def test_empty_file_raises_empty():
    with pytest.raises(EmptyResume):
        extract_text("resume.txt", b"   ")


def test_unsupported_suffix_raises():
    with pytest.raises(UnsupportedFormat):
        extract_text("resume.rtf", b"hello")
```

- [ ] **Step 4: Run the tests and confirm they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_text.py -q`
Expected: FAIL with `ModuleNotFoundError: app.services.resume_text`.

- [ ] **Step 5: Implement `extract_text`**

Use this dispatch and error mapping:

- Normalize the suffix with `Path(filename).suffix.lower()`; unsupported → `UnsupportedFormat`.
- `.txt`: decode UTF-8, fall back to latin-1, never raise on bad bytes.
- `.pdf`: `pypdf.PdfReader(io.BytesIO(data))`; join `page.extract_text() or ""`. Wrap any pypdf exception in `EmptyResume`.
- `.docx`: `docx.Document(io.BytesIO(data))`; join paragraph text and all table-cell text. Wrap parse exceptions in `EmptyResume`.
- Normalize: collapse spaces/tabs to one, collapse 3+ newlines to two, strip.
- If the result is empty → `EmptyResume`.
- Truncate to `max_chars`.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_text.py -q`
Expected: `11 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/services/resume_text.py backend/tests/test_resume_text.py backend/tests/fixtures/sample_resume.pdf
git commit -m "feat(backend): extract resume text from pdf, docx, and txt" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: JSON-Schema output and context cap in the LLM client

**Files:**
- Modify: `backend/app/llm/client.py:43-99`
- Create: `backend/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `Settings.llm_num_ctx`.
- Produces: `LLMClient.complete_json(..., json_schema: dict | None = None) -> object`
- Produces: `LLMClient.complete(..., json_schema: dict | None = None) -> str`

- [ ] **Step 1: Write the failing client tests**

```python
# backend/tests/test_llm_client.py
import pytest

from app.llm.client import LLMClient

SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": '{"name": "Priya"}'}}


def capture_post(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeResponse()

    monkeypatch.setattr("app.llm.client.httpx.post", fake_post)
    return captured


def test_schema_is_sent_as_format_and_num_ctx_is_capped(monkeypatch):
    captured = capture_post(monkeypatch)
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    result = client.complete_json("system", "user", model="qwen3:4b", json_schema=SCHEMA)
    assert result == {"name": "Priya"}
    assert captured["format"] == SCHEMA
    assert captured["options"]["num_ctx"] == 8192
    assert captured["think"] is False


def test_plain_json_mode_still_works(monkeypatch):
    captured = capture_post(monkeypatch)
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    client.complete_json("system", "user", model="lfm3:1.7b")
    assert captured["format"] == "json"
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_llm_client.py -q`
Expected: FAIL with `TypeError: complete_json() got an unexpected keyword argument 'json_schema'`.

- [ ] **Step 3: Implement**

- Add `self.num_ctx = settings.llm_num_ctx` in `__init__`.
- Add `json_schema: dict | None = None` to `complete` and `complete_json`.
- In `_ollama`, pass `num_ctx` inside `options`; set `payload["format"] = json_schema` when given, else `"json"` when `json_mode`.
- `complete_json` forwards `json_schema` and keeps the existing "Return ONLY valid JSON" instruction.
- OpenAI/Anthropic branches unchanged.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_llm_client.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/client.py backend/tests/test_llm_client.py
git commit -m "feat(llm): support schema-constrained output and context cap" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: Profile models, happy-path parse, and deterministic reconciliation

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/services/resume_parse.py`
- Create: `backend/tests/factories.py`
- Create: `backend/tests/test_resume_parse.py`

**Interfaces:**
- Produces: `ExperienceEntry`, `EducationEntry`, `LLMParsedProfile`, `ResumeProfile` (adds `canonical_skills`), and `ResumeRead` in `app.schemas`.
- Produces: `parse_resume_text(text: str, *, client: LLMClient | None = None) -> tuple[ResumeProfile, str]`.

- [ ] **Step 1: Write the failing happy-path tests**

```python
# backend/tests/factories.py
from app.schemas import ResumeProfile

FULL_PROFILE = {
    "name": "Priya Sharma",
    "email": "priya@example.com",
    "phone": "+91 98765 43210",
    "location": "Bengaluru",
    "summary": "Junior data scientist.",
    "total_years_experience": 1.5,
    "seniority": "junior",
    "target_roles": ["data scientist"],
    "preferred_locations": ["Bengaluru", "remote"],
    "remote_ok": True,
    "salary_min": 14,
    "salary_max": 18,
    "currency": "INR",
    "skills": ["Python", "LangChain"],
    "experience": [
        {"title": "Data Scientist", "company": "Acme", "start": "2025", "end": "present", "highlights": []}
    ],
    "education": [{"degree": "B.Tech", "institution": "VIT", "year": "2024"}],
    "certifications": [],
    "projects": [],
}


def make_profile() -> ResumeProfile:
    return ResumeProfile(**FULL_PROFILE, canonical_skills=["python", "langchain"])
```

```python
# backend/tests/test_resume_parse.py
import pytest
from pydantic import ValidationError

from app.schemas import LLMParsedProfile
from app.services.resume_parse import parse_resume_text
from tests.factories import FULL_PROFILE


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete_json(self, system, user, *, model, max_tokens, json_schema=None):
        self.calls.append((model, json_schema))
        if not self.responses:
            raise AssertionError("unexpected extra LLM call")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_returns_validated_profile_and_model():
    client = FakeClient([FULL_PROFILE])
    profile, model = parse_resume_text("Expected 14-18 LPA", client=client)
    assert model == "qwen3:4b"
    assert profile.name == "Priya Sharma"
    assert profile.experience[0].company == "Acme"
    assert client.calls[0][0] == "qwen3:4b"
    assert client.calls[0][1]["required"]


def test_lpa_is_reconciled_deterministically():
    profile, _ = parse_resume_text("Expected 14-18 LPA", client=FakeClient([FULL_PROFILE]))
    assert (profile.salary_min, profile.salary_max, profile.currency) == (1_400_000, 1_800_000, "INR")


def test_monthly_stipend_is_annualized():
    monthly = dict(FULL_PROFILE, salary_min=25_000, salary_max=35_000)
    profile, _ = parse_resume_text(
        "Stipend 25,000-35,000 per month", client=FakeClient([monthly])
    )
    assert (profile.salary_min, profile.salary_max) == (300_000, 420_000)


def test_inverted_salary_is_discarded():
    inverted = dict(FULL_PROFILE, salary_min=900_000, salary_max=500_000)
    profile, _ = parse_resume_text("No salary stated", client=FakeClient([inverted]))
    assert profile.salary_min is None and profile.salary_max is None


def test_canonical_skills_come_from_the_text():
    text = "Skills: Python, SQL, pandas, LangChain, Docker"
    profile, _ = parse_resume_text(text, client=FakeClient([dict(FULL_PROFILE, skills=[])]))
    assert set(profile.canonical_skills) >= {"python", "sql", "pandas", "langchain", "docker"}


def test_all_profile_fields_are_required():
    partial = {k: v for k, v in FULL_PROFILE.items() if k != "summary"}
    with pytest.raises(ValidationError):
        LLMParsedProfile.model_validate(partial)
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_parse.py -q`
Expected: FAIL with `ModuleNotFoundError: app.services.resume_parse`.

- [ ] **Step 3: Add the schemas**

- `ExperienceEntry`: `title`, `company` required; `start`, `end` default `""`; `highlights` default `[]`.
- `EducationEntry`: `degree`, `institution` required; `year` default `""`.
- `LLMParsedProfile`: every field listed in the design, all required (no defaults) so missing keys fail validation. `total_years_experience` is `float` with `ge=0, le=60`; `salary_min`/`salary_max` are `int | None` with `ge=0`; `seniority` is a `Literal["intern", "junior", "mid", "senior", "lead"]`.
- `ResumeProfile(LLMParsedProfile)`: adds required `canonical_skills: list[str]`.
- `ResumeRead`: `id, filename, profile: ResumeProfile, parse_model, content_hash, created_at`, with `from_attributes=True`.

- [ ] **Step 4: Implement `resume_parse.py`**

- `SYSTEM_PROMPT` states: copy facts exactly; never invent; use `""`/`null`/`[]` for absent values; `total_years_experience` is summed work duration in years; salary is annual in the resume's currency; monthly stipend ×12; Indian LPA ×100000; `target_roles` are job titles, never locations or sentences.
- `parse_resume_text` calls `client.complete_json(SYSTEM_PROMPT, "RESUME:\n" + text, model=settings.llm_parse_model, max_tokens=2048, json_schema=LLMParsedProfile.model_json_schema())`, then `LLMParsedProfile.model_validate(result)`.
- Reconcile:
  - `parse_salary(text)` wins when it returns a min.
  - Otherwise, if the text matches `per month|monthly|/\s*month|stipend` (case-insensitive), currency is `INR`, and the higher LLM bound is below 200,000, multiply both bounds by 12.
  - Negative bounds, or `min > max` when both exist → both `None`.
  - `canonical_skills = extract_skills(text)`.
- Return `(ResumeProfile(**profile.model_dump(), canonical_skills=...), settings.llm_parse_model)`.

- [ ] **Step 5: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_parse.py -q`
Expected: `6 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/services/resume_parse.py backend/tests/factories.py backend/tests/test_resume_parse.py
git commit -m "feat(backend): parse validated ATS profiles from resume text" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: Retry, fallback, and heuristic profile

**Files:**
- Modify: `backend/app/services/resume_parse.py`
- Modify: `backend/tests/test_resume_parse.py`

**Interfaces:**
- Extends: `parse_resume_text` returns `parse_model` set to the model that supplied the accepted JSON, or `"heuristic-v1"`.
- Consumes: `Settings.llm_fallback_model`, `parse_salary`, `extract_skills`.

- [ ] **Step 1: Write the failing failure-path tests**

```python
def test_invalid_then_valid_retries_primary():
    partial = {k: v for k, v in FULL_PROFILE.items() if k != "summary"}
    client = FakeClient([partial, FULL_PROFILE])
    profile, model = parse_resume_text("Python", client=client)
    assert profile.summary == "Junior data scientist."
    assert model == "qwen3:4b"
    assert [call[0] for call in client.calls] == ["qwen3:4b", "qwen3:4b"]


def test_invalid_primary_twice_uses_fallback():
    partial = {k: v for k, v in FULL_PROFILE.items() if k != "summary"}
    client = FakeClient([partial, partial, FULL_PROFILE])
    profile, model = parse_resume_text("Python", client=client)
    assert profile.summary == "Junior data scientist."
    assert model == "llama3.2:3b"


def test_all_invalid_returns_heuristic_profile():
    partial = {k: v for k, v in FULL_PROFILE.items() if k != "summary"}
    client = FakeClient([partial, partial, partial])
    profile, model = parse_resume_text("Expected 8-10 LPA. Skills: Python, SQL", client=client)
    assert model == "heuristic-v1"
    assert profile.name == ""
    assert (profile.salary_min, profile.salary_max) == (800_000, 1_000_000)
    assert set(profile.canonical_skills) >= {"python", "sql"}


def test_transport_error_uses_fallback_then_heuristic():
    from app.llm.client import LLMError

    client = FakeClient([LLMError("down"), LLMError("down")])
    profile, model = parse_resume_text("Skills: Python", client=client)
    assert model == "heuristic-v1"
    assert "python" in profile.canonical_skills
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_parse.py -q`
Expected: the new tests FAIL because retries/fallback are not implemented.

- [ ] **Step 3: Implement the attempt sequence**

1. Try the primary model.
2. On `ValidationError`, retry the primary once, appending the validation error to the user prompt.
3. On a second validation failure, or on `LLMError`/`httpx.HTTPError`, try `settings.llm_fallback_model` once (skip if empty or equal to the primary).
4. If every attempt fails, return `_heuristic_profile(text)` with `"heuristic-v1"`.
5. Catch only `ValidationError`, `LLMError`, and `httpx.HTTPError`; let genuine programming errors raise.

`_heuristic_profile` fills every required field: empty strings/lists, `seniority="mid"`, `total_years_experience=0`, `remote_ok=("remote" in text.lower())`, salary from `parse_salary`, `skills=canonical_skills=extract_skills(text)`.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resume_parse.py -q`
Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/resume_parse.py backend/tests/test_resume_parse.py
git commit -m "feat(backend): retry, fall back, and degrade to heuristic parsing" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: Deduplicating storage and embedding

**Files:**
- Create: `backend/app/services/resumes.py`
- Create: `backend/tests/test_resumes.py`

**Interfaces:**
- Produces: `create_resume(session: Session, filename: str, data: bytes, *, client: LLMClient | None = None) -> tuple[Resume, bool]`, where the bool is `True` when a new row was created.
- Produces: `content_hash(text: str) -> str`.
- Consumes: `extract_text`, `parse_resume_text`, `embed_texts`, `to_bytes`, `Resume`.

- [ ] **Step 1: Write the failing persistence tests**

```python
# backend/tests/test_resumes.py
import numpy as np
import pytest
from sqlmodel import select

from app.models import Resume
from app.services import resumes as service
from tests.factories import make_profile


@pytest.fixture
def fake_embed(monkeypatch):
    monkeypatch.setattr(service, "embed_texts", lambda texts: np.ones((len(texts), 384), dtype=np.float32))


def test_creates_resume_with_profile_and_embedding(session, fake_embed, monkeypatch):
    parsed = make_profile()
    monkeypatch.setattr(service, "parse_resume_text", lambda text, client=None: (parsed, "qwen3:4b"))
    row, created = service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")
    assert created is True
    assert row.id is not None
    assert row.parse_model == "qwen3:4b"
    assert row.profile["name"] == "Priya Sharma"
    assert len(row.embedding) == 384 * 4
    assert row.content_hash


def test_same_text_is_not_parsed_twice(session, fake_embed, monkeypatch):
    calls = []
    parsed = make_profile()

    def fake_parse(text, client=None):
        calls.append(text)
        return parsed, "qwen3:4b"

    monkeypatch.setattr(service, "parse_resume_text", fake_parse)
    first, created_first = service.create_resume(session, "a.txt", b"Priya   Sharma\nPython")
    second, created_second = service.create_resume(session, "b.txt", b"Priya Sharma\nPython")
    assert created_first is True and created_second is False
    assert first.id == second.id
    assert len(calls) == 1
    assert len(session.exec(select(Resume)).all()) == 1
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes.py -q`
Expected: FAIL with `ModuleNotFoundError: app.services.resumes`.

- [ ] **Step 3: Implement `create_resume`**

- `text = extract_text(filename, data, max_chars=settings.resume_max_chars)`.
- `digest = sha256(text.encode("utf-8")).hexdigest()`.
- Query `Resume.content_hash == digest`; if found return `(existing, False)` **before** parsing.
- Else `profile, parse_model = parse_resume_text(text, client=client)`.
- Embed `_embed_text(profile)` with `embed_texts([...])[0]`; store `to_bytes(vector)`.
- Insert and commit; `session.refresh(row)`; return `(row, True)`.
- `_embed_text` joins summary, target roles, skills, experience titles/companies, education, and projects.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/resumes.py backend/tests/test_resumes.py
git commit -m "feat(backend): store and deduplicate parsed resumes" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: HTTP endpoints

**Files:**
- Create: `backend/app/routers/resumes.py`
- Modify: `backend/app/main.py:8,27-28`
- Create: `backend/tests/test_resumes_api.py`

**Interfaces:**
- Produces: `POST /api/resumes` (`multipart/form-data`, field `file`) → `ResumeRead` with 201/200/413/415/422.
- Produces: `GET /api/resumes/{resume_id}` → `ResumeRead` with 200/404.
- Consumes: `create_resume`, `SUPPORTED_SUFFIXES`, `EmptyResume`, `UnsupportedFormat`.

- [ ] **Step 1: Write the failing API tests**

```python
# backend/tests/test_resumes_api.py
import io

import numpy as np
import pytest
from pypdf import PdfWriter

from app.services import resumes as service
from tests.factories import make_profile


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    monkeypatch.setattr(service, "embed_texts", lambda texts: np.ones((len(texts), 384), dtype=np.float32))
    monkeypatch.setattr(
        service,
        "parse_resume_text",
        lambda text, client=None: (make_profile(), "qwen3:4b"),
    )


def upload(api, name="priya.txt", content=b"Priya Sharma\nPython"):
    return api.post("/api/resumes", files={"file": (name, content, "text/plain")})


def test_upload_creates_resume(api):
    response = upload(api)
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "priya.txt"
    assert body["profile"]["name"] == "Priya Sharma"
    assert body["parse_model"] == "qwen3:4b"
    assert "text" not in body


def test_duplicate_upload_returns_existing(api):
    first = upload(api)
    second = upload(api, name="copy.txt")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_get_resume(api):
    created = upload(api).json()
    response = api.get(f"/api/resumes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_resume_returns_404(api):
    assert api.get("/api/resumes/9999").status_code == 404


def test_unsupported_format_returns_415(api):
    assert upload(api, name="resume.rtf").status_code == 415


def test_empty_file_returns_422(api):
    assert upload(api, content=b"").status_code == 422


def test_scanned_pdf_returns_422(api):
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    assert upload(api, name="scan.pdf", content=buffer.getvalue()).status_code == 422


def test_oversized_file_returns_413(api):
    payload = b"x" * (5 * 1024 * 1024 + 1)
    assert upload(api, content=payload).status_code == 413


def test_uppercase_txt_suffix_is_accepted(api):
    assert upload(api, name="RESUME.TXT").status_code == 201
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes_api.py -q`
Expected: FAIL with 404 because the route does not exist.

- [ ] **Step 3: Implement the router**

- `POST` is a sync `def` route taking `response: Response`, `file: UploadFile = File(...)`, `session=Depends(get_session)`.
- If `file.filename` is missing, treat it as `"resume"` (no suffix → 415).
- Check the suffix against `SUPPORTED_SUFFIXES` before reading; 415 otherwise.
- Read `settings.resume_max_bytes + 1` bytes; if longer, 413.
- Empty bytes → 422.
- Call `create_resume`; map `UnsupportedFormat` → 415 and `EmptyResume` → 422.
- Set `response.status_code = 201 if created else 200`; return `ResumeRead.model_validate(row)`.
- `GET` uses `session.get(Resume, resume_id)`; missing → 404.
- Include the router in `main.py` with `prefix="/api", tags=["resumes"]`.

- [ ] **Step 4: Run and confirm pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_resumes_api.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/resumes.py backend/app/main.py backend/tests/test_resumes_api.py
git commit -m "feat(api): add resume upload and retrieval endpoints" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: Config docs, full verification, and milestone close

**Files:**
- Modify: `backend/env.example`
- Modify: `CLAUDE.md`
- Modify: `PROGRESS.md`
- Create: `backend/tests/test_resume_parse_llm.py`

- [ ] **Step 1: Update `backend/env.example`**

Add below the LLM settings:

```ini
LLM_PARSE_MODEL=qwen3:4b
LLM_NUM_CTX=8192

# --- Resume upload ---
RESUME_MAX_BYTES=5242880
RESUME_MAX_CHARS=50000
```

Change the old `LLM_PARSE_MODEL=lfm3:1.7b` line to `qwen3:4b`.

- [ ] **Step 2: Batch the `CLAUDE.md` model note**

Replace the "Primary model" sentences with: parse `qwen3:4b` (2.5 GB, ~3.9 GB loaded),
rerank `lfm3:1.7b`, fallback `llama3.2:3b`. Note that `gemma4:12b` was tested and rejected
because it thrashed this 16 GB machine.

- [ ] **Step 3: Add the opt-in real-model test**

```python
# backend/tests/test_resume_parse_llm.py
import os

import pytest

from app.schemas import ResumeProfile
from app.services.resume_parse import parse_resume_text

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_TESTS") != "1", reason="set RUN_LLM_TESTS=1 to call the local model"
)

RESUMES = [
    ("junior", "Priya Sharma, data scientist, Python, LangChain. Expected 14-18 LPA."),
    ("fresher", "Arjun Mehta, final-year student. Python, SQL. Stipend 25,000-35,000 per month."),
    ("senior", "Rahul Verma, senior backend engineer, Python, Go. Expected 30-40 LPA."),
]


@pytest.mark.parametrize("label,text", RESUMES)
def test_qwen3_returns_a_valid_profile(label, text):
    profile, model = parse_resume_text(text)
    assert isinstance(profile, ResumeProfile)
    assert model == "qwen3:4b"
    assert profile.salary_min is not None and profile.salary_max is not None
    assert profile.salary_min >= 100_000  # annual, never a raw monthly stipend
```

Run: `cd backend && RUN_LLM_TESTS=1 .venv/bin/python -m pytest tests/test_resume_parse_llm.py -q`
Expected: `3 passed`. Without the env var these tests skip.

- [ ] **Step 4: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: all tests pass; the three `test_resume_parse_llm` tests skip unless enabled.

- [ ] **Step 5: Verify the existing pipeline still works**

Run: `cd backend && .venv/bin/python -m app.cli ingest`
Expected: JSON stats with `skipped` equal to the seed count and no errors (idempotent).

- [ ] **Step 6: Exercise the real endpoint end to end**

Start `uvicorn app.main:app --reload`, then with a real TXT, the generated PDF fixture, and a DOCX:

```bash
curl -s -F "file=@backend/tests/fixtures/sample_resume.pdf" http://localhost:8000/api/resumes | head -c 800
curl -s -F "file=@/path/to/real_resume.docx" http://localhost:8000/api/resumes | head -c 800
```

Expected: `201` first time and `200` on re-upload; `parse_model` is `qwen3:4b`;
salary is annual INR; no throttling or swap growth while Qwen3 runs.

- [ ] **Step 7: Self-review the diff**

Run: `git diff --stat && git diff`
Check: no debug prints, no resume text in logs, no secrets, no unrelated edits.

- [ ] **Step 8: Update `PROGRESS.md`**

Set "Last done" to M2 with the commit range, "In progress" to none, "Next" to M3, and add
the invariant: parse uses `qwen3:4b`; `gemma4:12b` is rejected on this hardware; salary is
reconciled deterministically.

- [ ] **Step 9: Commit the milestone**

```bash
git add backend/env.example CLAUDE.md PROGRESS.md backend/tests/test_resume_parse_llm.py
git commit -m "docs: close M2 and record parse model decision" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

Do not push until the full suite and the real-file check both pass. Then a single push of
the branch is allowed as the M2 milestone boundary.
