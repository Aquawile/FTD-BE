#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/isabellabutera/app/app}"
VENV_DIR="${VENV_DIR:-/home/isabellabutera/app/.venv}"
LOG_FILE="${LOG_FILE:-/tmp/uvicorn.log}"
HOST="${HOST:-127.0.0.1}"  # Default to localhost for security; override to 0.0.0.0 for multi-VM staging

export PGHOST="${PGHOST:-10.168.0.3}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-ftd_lakehouse_api_test}"
export PGUSER="${PGUSER:-ftd_app}"
export PGPASSWORD="${PGPASSWORD:-}"

export FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-ftd-2026}"
export FIREBASE_CREDENTIALS_PATH="${FIREBASE_CREDENTIALS_PATH:-/home/isabellabutera/firebase-key.json}"
export FIREBASE_AUTH_ENABLED="${FIREBASE_AUTH_ENABLED:-true}"

if [[ -z "${PGPASSWORD}" ]]; then
  echo "ERROR: PGPASSWORD is not set" >&2
  exit 1
fi

cd "${APP_DIR}"

echo "Starting FastAPI on ${HOST}:8000..."
nohup "${VENV_DIR}/bin/uvicorn" app.main:app --host "${HOST}" --port 8000 > "${LOG_FILE}" 2>&1 &
echo $! > /tmp/uvicorn.pid
echo "FastAPI started (PID $(cat /tmp/uvicorn.pid))"
