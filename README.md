# FLA Job Finder

A job finder for Forward Learning Academy students: upload a resume, set your
preferences, and get ranked roles with a fit score, reasons, and skill gaps.

> **v1 status:** internal demo. Seed data only, no login, no live job feeds.

## Prerequisites

- Python 3.14 and Node 20+
- [Ollama](https://ollama.com) with the local model pulled: `ollama pull lfm3:1.7b`

No cloud API keys are used. Parsing and scoring run entirely on your machine.

## Quickstart

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env              # defaults target local Ollama
python -m app.cli ingest         # load ~100 seed listings
uvicorn app.main:app --reload    # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

## How matching works

Two stages, so cost stays flat as the corpus grows:

1. **Retrieve** — SQL filters plus local embedding similarity narrow thousands of
   jobs to ~40 candidates. No LLM involved.
2. **Rerank** — the model scores only those ~40, returning a score, reasons, and
   missing skills. Results are cached per resume and job, so repeat searches are free.

## Layout

```
backend/    FastAPI + SQLModel
frontend/   React + Vite + TypeScript + Tailwind
data/       committed seed corpus
scripts/    seed builder and dev runner
```
