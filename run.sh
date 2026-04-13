#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

source "$ROOT/venv/bin/activate"

cd "$ROOT/backend"
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000
