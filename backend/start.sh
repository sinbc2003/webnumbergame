#!/bin/sh
set -eu

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${UVICORN_WORKERS:-1}"

echo "Starting number-game API on ${HOST}:${PORT} (workers: ${WORKERS})"
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"

