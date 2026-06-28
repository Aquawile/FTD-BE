#!/usr/bin/env bash
# Deploy the Reddit ingestion Cloud Function to GCP.
# Run from the reddit/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FUNCTION_DIR="${PROJECT_ROOT}/cloud-function"

: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${GCLOUD_REGION:=us-west2}"

echo "Deploying reddit-ingest Cloud Function to project=${GCP_PROJECT} region=${GCLOUD_REGION} ..."

if [[ ! -f "${FUNCTION_DIR}/.env" ]]; then
  if [[ -f "${FUNCTION_DIR}/.env.example" ]]; then
    echo "ERROR: ${FUNCTION_DIR}/.env not found. Copy .env.example and fill in INGESTION_API_KEY."
    exit 1
  else
    echo "ERROR: Missing ${FUNCTION_DIR}/.env.example"
    exit 1
  fi
fi

# Convert .env key=value pairs to comma-separated --set-env-vars format
ENV_VARS=$(grep -v '^#' "${FUNCTION_DIR}/.env" | grep -v '^$' | awk -F= '{print $1"="$2}' | paste -sd, -)

gcloud functions deploy reddit-ingest \
  --project="${GCP_PROJECT}" \
  --region="${GCLOUD_REGION}" \
  --runtime=python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=reddit_ingest \
  --source="${FUNCTION_DIR}" \
  --timeout=60s \
  --memory=256MB \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="${ENV_VARS}"

FUNCTION_URL=$(gcloud functions describe reddit-ingest \
  --project="${GCP_PROJECT}" \
  --region="${GCLOUD_REGION}" \
  --format='value(serviceConfig.uri)')

echo ""
echo "Deployment complete."
echo "Function URL: ${FUNCTION_URL}"
echo "Update devvit-app/.env with:"
echo "  INGESTION_ENDPOINT=${FUNCTION_URL}"
