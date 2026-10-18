#!/usr/bin/env bash
# data-ingest-vm startup script (instance metadata key: startup-script). Runs as
# root on every boot.
#
# The VM is started twice a day:
#   21:55 UTC  start-price-vm      -> ~/prices/run.sh (cron 22:00) fetches Finnhub
#                                     prices; its EXIT trap stops the VM (~22:09)
#   03:30 UTC  sec-8k-daily-start  -> this script runs the SEC 8-K check below;
#                                     src.main stops the VM when it finishes
# So the SEC check runs only on the 03:xx boot. On any other boot this script
# does nothing and leaves the VM to the job that started it. A boot-time unit
# (max-uptime-shutdown.service) powers the VM off 90 minutes after any boot.
#
# FORCE_SEC=1 runs the check regardless of the hour (manual testing).
set -euo pipefail

RUN_USER="isabellabutera"            # startup scripts run as root, which has no $USER
APP_DIR="/opt/sec-8k-ingestion"
LOG_DIR="/var/log/sec-8k-ingestion"
LOG_FILE="${LOG_DIR}/ingestion.log"
STOP_VM=(gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet)

hour="$(date -u +%H)"
if [[ "${hour}" != "03" && "${FORCE_SEC:-0}" != "1" ]]; then
  echo "Boot at ${hour}:xx UTC is not the SEC window (03:xx); leaving the VM to its other job."
  exit 0
fi

mkdir -p "${LOG_DIR}"
chown -R "${RUN_USER}:${RUN_USER}" "${LOG_DIR}"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo "Missing ${APP_DIR}/.env (copy .env.example); stopping VM." | tee -a "${LOG_FILE}"
  "${STOP_VM[@]}"
  exit 1
fi

echo "Starting SEC 8-K ingestion at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${LOG_FILE}"
status=0
sudo -u "${RUN_USER}" bash -c "cd '${APP_DIR}' && set -a && source .env && set +a && .venv/bin/python -m src.main" \
  >> "${LOG_FILE}" 2>&1 || status=$?
echo "SEC ingestion exited with code ${status} at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${LOG_FILE}"

# src.main stops the VM itself in a finally block; stop again in case it died before that.
"${STOP_VM[@]}" || true
exit "${status}"
