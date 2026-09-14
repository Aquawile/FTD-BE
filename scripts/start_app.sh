#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/isabellabutera/app}"
VENV_DIR="${VENV_DIR:-/home/isabellabutera/app/.venv}"
LOG_FILE="${LOG_FILE:-/tmp/uvicorn.log}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

export PGHOST="${PGHOST:-10.168.0.3}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-ftd_lakehouse_staging}"
export PGUSER="${PGUSER:-ftd_app}"
export PGPASSWORD="${PGPASSWORD:-}"

export FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-ftd-2026}"
export FIREBASE_AUTH_ENABLED="${FIREBASE_AUTH_ENABLED:-true}"

# Use ApplicationDefault() credentials; do not set FIREBASE_CREDENTIALS_PATH
# unless you have a service-account JSON key file at that path.

if [[ -z "${PGPASSWORD}" ]]; then
  echo "ERROR: PGPASSWORD is not set" >&2
  exit 1
fi

export PYTHONPATH="${APP_DIR}:${PYTHONPATH:-}"

cd "${APP_DIR}"

echo "Starting FastAPI on ${HOST}:${PORT}..."
nohup "${VENV_DIR}/bin/uvicorn" app.main:app --host "${HOST}" --port "${PORT}" > "${LOG_FILE}" 2>&1 &
echo $! > /tmp/uvicorn.pid
echo "FastAPI started (PID $(cat /tmp/uvicorn.pid))"
