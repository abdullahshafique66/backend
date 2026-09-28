#!/usr/bin/env bash
# Start the API on macOS/Linux: creates a virtual env the first time.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
else
  . .venv/bin/activate
fi
exec python -m uvicorn app.main:app --reload --port 8000
