# FLA Job Finder

Job finder for Forward Learning Academy students. Upload a resume, set filters
(experience, salary, location, role), get ranked openings with a fit score,
an explanation of why each fits, and the skills the student is missing.

v1 is an internal demo: seed jobs, no auth, no live job APIs.

## Commands

Local model, once per machine:

- `ollama pull lfm3:1.7b` — the default parse/rerank model (~1.7 GB)
- `ollama serve` — usually already running on :11434

Backend, from `backend/` with the venv active:

- `uvicorn app.main:app --reload` — API at http://localhost:8000, docs at `/docs`
- `python -m app.cli ingest` — load seed jobs, extract fields, embed. Idempotent.
- `pytest` — backend tests

Frontend, from `frontend/`:

- `npm run dev` — http://localhost:5173, proxies `/api` to :8000
- `npm run build` — typecheck and production build

Both at once: `./scripts/dev.sh`

## Current status

- **M1 done** (commits `6874a0d`, `5be0233`): seed corpus, normalization, idempotent
  ingest, local embeddings, `GET /api/jobs`, local LLM client, `/api/health/llm`.
- **Pending:** M2 resume upload/parse, M3 retrieval, M4 rerank + cache, M5 frontend, M6 tests/docs.
- Primary model `lfm3:1.7b`; fallback `llama3.2:3b` loads only on invalid JSON.
  Heavier models (e.g. `gemma4:12b`) are deliberately not used on this 16 GB machine.

## Layout

- `backend/app/sources/` — job providers behind the `JobSource` protocol
- `backend/app/services/` — ingestion, retrieval, ranking
- `backend/app/llm/` — the only place that talks to a model provider
- `backend/app/routers/` — thin HTTP layer; no business logic
- `frontend/src/api.ts` — the only module that calls the backend
- `data/seed_jobs.json` — committed demo corpus; the app never fetches at runtime

## Conventions

- Python 3.14, FastAPI, SQLModel, SQLite. Postgres + pgvector is the migration path.
- All ingestion goes through `app/sources/base.py`. Routers never call a provider directly.
- Every LLM call goes through `app/llm/client.py` and must be cache-safe: check the
  `matches` table before spending tokens.
- Pydantic models for every request and response body.
- Frontend: TypeScript strict, Tailwind, network calls only through `src/api.ts`.

## Gotchas

- The LLM is local (Ollama). Never point `LLM_BASE_URL` at a coding-plan or harness
  endpoint; those credentials are licensed for approved harnesses, not application calls.
- `.env` is gitignored; start from `env.example`.
- Small local models drop items from batch output. Always validate that every requested
  `job_id` came back before trusting a rerank response.
- Seed listings are demo data. The UI must show a "demo data" badge; never imply they are live.
- Do not scrape LinkedIn, Indeed, or Naukri. Real sources are official APIs or public ATS boards.

## Working agreement

This is Bhargav's first solo project for the company. Nothing else on this machine is a
valid reference. Ask before deciding anything about sources, deployment, naming, or
company-specific behavior.
