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
# Code delivery: on every boot this script first installs the latest release that
# the staging deploy published (gs://ftd2026-releases/data-ingest/CURRENT ->
# <sha>.tgz: SEC app, price fetcher, this VM's uptime unit) and makes sure the
# price cron entry exists, so the VM always runs what's on the staging branch
# without the deploy ever having to start this (expensive) VM. If the download
# fails, the installed code is used as-is.
#
# FORCE_SEC=1 runs the check regardless of the hour (manual testing).
# UPDATE_ONLY=1 installs the latest release and exits (used by the deploy when the
# VM happens to be running).
set -euo pipefail

RUN_USER="isabellabutera"            # startup scripts run as root, which has no $USER
APP_DIR="/opt/sec-8k-ingestion"
LOG_DIR="/var/log/sec-8k-ingestion"
LOG_FILE="${LOG_DIR}/ingestion.log"
STOP_VM=(gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet)
RELEASES="gs://ftd2026-releases/data-ingest"
RELEASE_STATE="/opt/ftd-release"
PRICES_DIR="/home/${RUN_USER}/prices"
PRICE_CRON="0 22 * * * ${PRICES_DIR}/run.sh"

install_latest_release() {
  local want have tmp old_req
  want="$(gcloud storage cat "${RELEASES}/CURRENT" 2>/dev/null | tr -d '[:space:]' || true)"
  have="$(cat "${RELEASE_STATE}/SHA" 2>/dev/null || true)"
  if [[ -z "${want}" ]]; then
    echo "release: no CURRENT pointer found; keeping installed code (${have:-unknown})"
  elif [[ "${want}" == "${have}" ]]; then
    echo "release: ${have} already installed"
  else
    tmp="$(mktemp -d)"
    if gcloud storage cp "${RELEASES}/${want}.tgz" "${tmp}/release.tgz" --quiet && tar -xzf "${tmp}/release.tgz" -C "${tmp}"; then
      # Each step must succeed, or the release isn't marked installed (and is retried next boot).
      old_req="$(md5sum "${APP_DIR}/requirements.txt" 2>/dev/null | cut -d' ' -f1 || true)"
      if mkdir -p "${APP_DIR}" \
         && cp -a "${tmp}/sec/." "${APP_DIR}/" \
         && chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}" \
         && { [[ "$(md5sum "${APP_DIR}/requirements.txt" | cut -d' ' -f1)" == "${old_req}" || ! -x "${APP_DIR}/.venv/bin/pip" ]] \
              || sudo -u "${RUN_USER}" "${APP_DIR}/.venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"; } \
         && install -d -o "${RUN_USER}" -g "${RUN_USER}" "${PRICES_DIR}" \
         && install -o "${RUN_USER}" -g "${RUN_USER}" -m 755 "${tmp}/prices/run.sh" "${PRICES_DIR}/run.sh" \
         && install -o "${RUN_USER}" -g "${RUN_USER}" -m 644 "${tmp}/prices/main.py" "${tmp}/prices/requirements.txt" "${PRICES_DIR}/" \
         && install -m 644 "${tmp}/deploy/max-uptime-shutdown.service" /etc/systemd/system/max-uptime-shutdown.service \
         && systemctl daemon-reload && systemctl enable --quiet max-uptime-shutdown.service; then
        mkdir -p "${RELEASE_STATE}" && echo "${want}" > "${RELEASE_STATE}/SHA"
        echo "release: installed ${want} (was ${have:-unknown})"
      else
        echo "release: install of ${want} failed part-way; will retry next boot"
      fi
    else
      echo "release: could not download ${want}; keeping installed code (${have:-unknown})"
    fi
    rm -rf "${tmp}"
  fi
  if ! crontab -u "${RUN_USER}" -l 2>/dev/null | grep -qxF "${PRICE_CRON}"; then
    { crontab -u "${RUN_USER}" -l 2>/dev/null || true; echo "${PRICE_CRON}"; } | crontab -u "${RUN_USER}" -
    echo "cron: added '${PRICE_CRON}'"
  fi
}

install_latest_release || echo "release: update step failed; continuing with installed code"
if [[ "${UPDATE_ONLY:-0}" == "1" ]]; then
  exit 0
fi

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
