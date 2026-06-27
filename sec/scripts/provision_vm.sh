#!/usr/bin/env bash
# Creates the ingestion VM if it does not already exist.
# Review variables, then run manually when you are ready to provision — not part of the pipeline.
set -euo pipefail

: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${GCE_INSTANCE_NAME:=data-ingest-vm}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
IMAGE_FAMILY="${IMAGE_FAMILY:-debian-12}"
IMAGE_PROJECT="${IMAGE_PROJECT:-debian-cloud}"
BOOT_DISK_SIZE="${BOOT_DISK_SIZE:-30GB}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-}"

if gcloud compute instances describe "${GCE_INSTANCE_NAME}" \
  --project="${GCP_PROJECT}" \
  --zone="${GCE_ZONE}" >/dev/null 2>&1; then
  echo "Instance ${GCE_INSTANCE_NAME} already exists in ${GCE_ZONE}."
  exit 0
fi

create_args=(
  gcloud compute instances create "${GCE_INSTANCE_NAME}"
  --project="${GCP_PROJECT}"
  --zone="${GCE_ZONE}"
  --machine-type="${MACHINE_TYPE}"
  --image-family="${IMAGE_FAMILY}"
  --image-project="${IMAGE_PROJECT}"
  --boot-disk-size="${BOOT_DISK_SIZE}"
  --scopes=storage-full,cloud-platform
  --metadata=enable-oslogin=TRUE
  --tags=sec-ingest
)

if [[ -n "${SERVICE_ACCOUNT}" ]]; then
  create_args+=(--service-account="${SERVICE_ACCOUNT}")
fi

"${create_args[@]}"
echo "Created ${GCE_INSTANCE_NAME}. Grant Storage Object Admin on raw-data-strg to its service account."
