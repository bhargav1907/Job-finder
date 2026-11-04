# M2 — Resume upload and parse: design

Date: 2026-11-04
Status: awaiting approval

## Intent

A student uploads a resume (PDF, DOCX, or TXT) and receives a structured profile:
contact basics, summary, experience, education, skills, preferences. That profile is
what M3 (retrieval) and M4 (rerank + explanation) will compare against seed jobs, and
what the frontend will use to prefill filters.

Success: a real student resume comes back as a validated full ATS profile in one
upload, in under ~20 seconds, without the machine swapping. A malformed or unreadable
file gets a clear error; a model failure still leaves a usable resume record.

## Goals

- Accept `.pdf`, `.docx`, `.txt`; reject unsupported or oversized files clearly.
- Extract clean text locally. No network, no OCR.
- Parse the full ATS profile with the local model, constrained to a JSON Schema.
- Validate with Pydantic; repair/retry once; fall back to a heuristic profile rather
  than failing the request.
- Store filename, text, profile, embedding, content hash, and parse model in SQLite.
  Do not retain the uploaded file.
- Deduplicate identical resumes by content hash so a re-upload costs no LLM call.
- Expose the parsed resume over HTTP for M3 and the frontend.

## Non-goals

- OCR for scanned/image-only PDFs.
- Resume editing or rewriting.
- Matching or ranking (M3/M4).
- The frontend upload UI (M5).
- Auth, multi-user separation, file retention, or PII retention policy beyond the demo.
- DOCX styling fidelity. We extract text, not layout.

## Anti-goals

- Returning a half-parsed profile silently. Partial parses are labelled by `parse_model`.
- Sending resume text to any hosted model.
- A model that needs more than ~4 GB loaded on this 16 GB M1 Pro.
- Storing a configurable/edited profile copy that drifts from the parsed source.

## Constraints

- Python 3.14, FastAPI, SQLModel, SQLite; existing `Resume` table already has every
  column this design needs, so **no database schema change**.
- Local models only. Parsing uses `qwen3:4b` (2.5 GB, ~3.9 GB loaded at 8K context,
  12–16 s per resume, no swap growth in testing). Rerank stays on `lfm3:1.7b`.
  `llama3.2:3b` is the validation fallback.
- One new dependency: `python-docx` 1.2.0, verified on PyPI.
- `pypdf` and `python-multipart` are already installed but unused.
- Cache before tokens: identical text never reaches the model twice.

## Approaches considered

1. **Single schema-constrained LLM call + deterministic reconciliation (chosen).**
   One call per new resume, Ollama `format` set to the Pydantic JSON Schema, validate,
   then correct salary and canonical skills from deterministic code. Simple, one slow
   call, and the schema removes malformed/partial JSON as a failure mode.
2. **Two-stage parsing** — split into sections, call once per section. Better on long
   resumes, but 4–6 calls, more orchestration, and student resumes are 1–2 pages. Rejected
   for v1.
3. **Deterministic-only parsing** — regex for skills/salary/seniority. Instant and free,
   but cannot produce work-history entries, education, projects, or a summary. Rejected
   because the deliverable is a full ATS profile.

Model options measured on three resumes (same schema):

| Model | Weights/loaded | Time | Salary units | Roles | Verdict |
|---|---|---|---|---|---|
| `qwen3:4b` | 2.5 / 3.9 GB | 12–16 s | correct with prompt rule | job titles | **chosen** |
| `phi4-mini:3.8b` | 2.5 / 3.6 GB | 16 s | 10× too high | locations | rejected, removed |
| `llama3.2:3b` | 2.0 / 3.0 GB | 9–10 s | stipend treated as annual | vague/empty | fallback only |
| `gemma4:12b` | 7.7 / 8+ GB | 61 s | correct | correct | rejected, throttled the Mac |

## Design

### API (new public surface)

`POST /api/resumes` — `multipart/form-data`, field `file`.

- `201` with `ResumeRead` when a new resume is stored.
- `200` with the existing `ResumeRead` when `content_hash` matches a stored resume.
- `413` file larger than `RESUME_MAX_BYTES` (5 MB).
- `415` extension/content type not in `{pdf, docx, txt}`.
- `422` no extractable text (empty file, scanned PDF, corrupt document).
- `200` is still possible when the LLM failed: `parse_model` is `"heuristic-v1"` and
  the profile carries the deterministic subset. The request does not fail because the
  local model is down.

`GET /api/resumes/{resume_id}` — `200 ResumeRead`, `404` if absent.

`ResumeRead`:
`id, filename, profile, parse_model, content_hash, created_at`.

`profile` is `ResumeProfile` (below). No raw text in the response; it stays in SQLite.

### Profile schema (one source of truth)

`LLMParsedProfile` — exactly what the model must return; its `model_json_schema()` is
passed to Ollama as `format`:

- `name, email, phone, location, summary`: strings
- `total_years_experience`: number, 0–60
- `seniority`: enum `intern | junior | mid | senior | lead`
- `target_roles, preferred_locations`: arrays of strings
- `remote_ok`: boolean
- `salary_min, salary_max`: integer or null; `currency`: string
- `skills`: array of strings
- `experience`: array of `{title, company, start, end, highlights[]}`
- `education`: array of `{degree, institution, year}`
- `certifications, projects`: arrays of strings

`ResumeProfile` extends it with `canonical_skills: list[str]`, added server-side and not
requested from the model. It is what M3 compares against job canonical skills.

### Deterministic reconciliation

- **Salary** — `normalize.parse_salary(text)` is authoritative when it returns values.
  It already understands Indian LPA. The prompt separately instructs monthly → ×12 and
  LPA → ×100000 for stipend/LPA cases the regex misses; LLM values are used only when
  the regex returns none. Both bounds are sanity-checked (`0 <= min <= max`).
- **Canonical skills** — `normalize.extract_skills(text)` populates `canonical_skills`.
  The model's `skills` remain as written for display.
- **Seniority** — take the model's enum after validation; no heuristic override.

### Parsing flow

1. Size-check and read the upload (cap at 5 MB).
2. Dispatch on suffix: PDF via `pypdf`, DOCX via `python-docx` (paragraphs + table
   cells), TXT via UTF-8 with a latin-1 fallback. Normalize whitespace and cap at
   50,000 characters.
3. `content_hash = sha256(normalized_text)`. If it exists, return that resume; stop.
4. Call `LLMClient.complete_json(..., model=settings.llm_parse_model,
   json_schema=LLMParsedProfile.model_json_schema(), max_tokens=2048)`.
5. Validate into `LLMParsedProfile`. On failure, retry once with the validation error in
   the prompt; then try `settings.llm_fallback_model`; then build the heuristic profile.
6. Reconcile salary and canonical skills; embed the profile
   (`summary + skills + experience + education + projects`) with the existing
   `embed_texts`/`to_bytes`.
7. Insert `Resume(filename, text, profile, embedding, content_hash, parse_model)`,
   commit, return.

No resume text is logged; errors report only the filename, size, and failure class.

### Client and config changes

- `LLMClient.complete_json` gains `json_schema: dict | None`. For Ollama, `format`
  becomes the schema; without it, behaviour is unchanged (`"json"`). OpenAI/Anthropic
  branches keep current behaviour.
- Ollama payload gains `options.num_ctx` from a new `llm_num_ctx` setting (default
  8192). Without a cap, Qwen's large default context wastes memory.
- `llm_parse_model` default becomes `qwen3:4b`. `llm_rerank_model` stays `lfm3:1.7b`;
  `llm_fallback_model` stays `llama3.2:3b`.
- New settings: `resume_max_bytes` (5 MiB), `resume_max_chars` (50,000).
  `.env.example` and the model notes in `CLAUDE.md` updated.

### Module layout

- `backend/app/services/resume_text.py` — format dispatch and text extraction.
  Raises `UnsupportedFormat` / `EmptyResume`.
- `backend/app/services/resume_parse.py` — prompt, model call, validation, retry,
  reconciliation, embedding text.
- `backend/app/services/resumes.py` — hash/dedupe, orchestration, persistence.
- `backend/app/routers/resumes.py` — thin HTTP layer, maps exceptions to status codes.
- `backend/app/schemas.py` — profile models and `ResumeRead`.
- `backend/tests/` — new; this milestone establishes the test layout.

### Tests

- Extraction: TXT (UTF-8 and latin-1), DOCX generated in-test with `python-docx`,
  PDF fixture file, empty/scanned-PDF error, unsupported suffix, oversize.
- Parsing: fake `LLMClient` returning valid JSON, invalid-then-valid (retry), invalid
  twice (fallback), malformed salary corrected by `parse_salary`, canonical skills added.
- API: create (201), duplicate (200, one LLM call), get (200/404), 413/415/422.
  Session dependency overridden to a temporary SQLite database.
- Optional integration marked `llm` (skipped unless `RUN_LLM_TESTS=1`) runs the three
  real resumes from the model benchmark and asserts schema validity.
- No test is weakened to pass; the real suite runs once before reporting.

## Decisions left to the builder

- Exact prompt wording (versioned constant `RESUME_PROMPT_VERSION = "v1"`).
- PDF fixture generation method (a tiny committed PDF vs. monkeypatched reader).
- Whether to add a `GET /api/resumes` list endpoint later; not needed for M2.
- Token budget for retries and whether to keep the first failure's raw output on disk
  for debugging (design says no; keep errors in memory only).

## Rollout

No migration. Existing `resumes` table is empty in the demo DB. Run
`pytest`, then exercise `POST /api/resumes` against the dev server with one real PDF,
one DOCX, and one TXT. Update `PROGRESS.md` and commit locally; no push until the M2
milestone is verified.

## Approval needed

This design adds a dependency (`python-docx`), two public endpoints
(`POST /api/resumes`, `GET /api/resumes/{id}`), and changes the default parse model to
`qwen3:4b`. Confirm those before implementation.
