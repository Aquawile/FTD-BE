#!/usr/bin/env bash
# Installs Python dependencies on the GCP VM.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sec-8k-ingestion}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${USER}:${USER}" "${APP_DIR}"

cd "${APP_DIR}"
${PYTHON_BIN} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed in ${APP_DIR}/.venv"
