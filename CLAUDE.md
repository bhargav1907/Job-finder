# FLA Job Finder

Job finder for Forward Learning Academy students. Upload a resume, set filters
(experience, salary, location, role), get ranked openings with a fit score,
an explanation of why each fits, and the skills the student is missing.

v1 is an internal demo: seed jobs, no auth, no live job APIs.

## Commands

Backend, from `backend/` with the venv active:

- `uvicorn app.main:app --reload` — API at http://localhost:8000, docs at `/docs`
- `python -m app.cli ingest` — load seed jobs, extract fields, embed. Idempotent.
- `pytest` — backend tests

Frontend, from `frontend/`:

- `npm run dev` — http://localhost:5173, proxies `/api` to :8000
- `npm run build` — typecheck and production build

Both at once: `./scripts/dev.sh`

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

- `.env` is gitignored. Use a dedicated `ARK_API_KEY`; never the Claude Code auth token.
- Seed listings are demo data. The UI must show a "demo data" badge; never imply they are live.
- Do not scrape LinkedIn, Indeed, or Naukri. Real sources are official APIs or public ATS boards.

## Working agreement

This is Bhargav's first solo project for the company. Nothing else on this machine is a
valid reference. Ask before deciding anything about sources, deployment, naming, or
company-specific behavior.
