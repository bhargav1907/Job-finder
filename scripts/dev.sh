#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x backend/.venv/bin/python ]; then
  echo "backend/.venv is missing. Create it first:" >&2
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate" >&2
  echo "  pip install -r requirements.txt" >&2
  exit 1
fi

(
  cd backend
  .venv/bin/python -m uvicorn app.main:app --reload
) &
backend_pid=$!

trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM

cd frontend
npm run dev
