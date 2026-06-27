#!/usr/bin/env bash
# Creates Cloud Scheduler job to start the ingestion VM daily at 03:30 UTC.
# Review and edit variables before running — do not execute until GCP resources exist.
set -euo pipefail

: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${GCE_INSTANCE_NAME:=data-ingest-vm}"
: "${SCHEDULER_SERVICE_ACCOUNT:?Set SCHEDULER_SERVICE_ACCOUNT}"

SCHEDULER_JOB_NAME="${SCHEDULER_JOB_NAME:-sec-8k-daily-start}"
SCHEDULER_LOCATION="${SCHEDULER_LOCATION:-us-west2}"
CRON_SCHEDULE="${CRON_SCHEDULE:-30 3 * * *}"

if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" \
  --project="${GCP_PROJECT}" \
  --location="${SCHEDULER_LOCATION}" >/dev/null 2>&1; then
  echo "Updating existing scheduler job ${SCHEDULER_JOB_NAME}"
  gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
    --project="${GCP_PROJECT}" \
    --location="${SCHEDULER_LOCATION}" \
    --schedule="${CRON_SCHEDULE}" \
    --time-zone="UTC" \
    --uri="https://compute.googleapis.com/compute/v1/projects/${GCP_PROJECT}/zones/${GCE_ZONE}/instances/${GCE_INSTANCE_NAME}/start" \
    --http-method=POST \
    --oauth-service-account-email="${SCHEDULER_SERVICE_ACCOUNT}"
else
  gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
    --project="${GCP_PROJECT}" \
    --location="${SCHEDULER_LOCATION}" \
    --schedule="${CRON_SCHEDULE}" \
    --time-zone="UTC" \
    --uri="https://compute.googleapis.com/compute/v1/projects/${GCP_PROJECT}/zones/${GCE_ZONE}/instances/${GCE_INSTANCE_NAME}/start" \
    --http-method=POST \
    --oauth-service-account-email="${SCHEDULER_SERVICE_ACCOUNT}" \
    --description="Start SEC 8-K ingestion VM daily at 03:30 UTC"
fi

echo "Scheduler job '${SCHEDULER_JOB_NAME}' configured for ${CRON_SCHEDULE} UTC."
