#!/usr/bin/env bash
# VM startup script — runs automatically when Cloud Scheduler starts the instance.
# Attach via instance metadata key: startup-script (or use this as a systemd unit).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sec-8k-ingestion}"
ENV_FILE="${APP_DIR}/.env"
LOG_DIR="/var/log/sec-8k-ingestion"
LOG_FILE="${LOG_DIR}/ingestion.log"

sudo mkdir -p "${LOG_DIR}"
sudo chown -R "${USER}:${USER}" "${LOG_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.example and fill in values before scheduling."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

cd "${APP_DIR}"
source .venv/bin/activate

echo "Starting SEC 8-K ingestion at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
python -m src.main 2>&1 | tee -a "${LOG_FILE}"
exit_code=${PIPESTATUS[0]}
echo "Pipeline exited with code ${exit_code} at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
exit "${exit_code}"
