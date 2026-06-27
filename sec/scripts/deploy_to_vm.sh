#!/usr/bin/env bash
# Package and upload the sec/ pipeline to the GCP VM.
# Run from anywhere; resolves paths relative to this script's sec/ root.
set -euo pipefail

SEC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${GCE_INSTANCE_NAME:=data-ingest-vm}"

cd "${SEC_ROOT}"
tar --exclude='.venv' --exclude='__pycache__' --exclude='.env' -czf /tmp/sec-8k-ingestion.tgz .
gcloud compute scp /tmp/sec-8k-ingestion.tgz "${GCE_INSTANCE_NAME}:/tmp/" \
  --zone="${GCE_ZONE}" \
  --project="${GCP_PROJECT}" \
  --quiet

gcloud compute ssh "${GCE_INSTANCE_NAME}" \
  --zone="${GCE_ZONE}" \
  --project="${GCP_PROJECT}" \
  --quiet \
  --command='
set -euo pipefail
sudo mkdir -p /opt/sec-8k-ingestion
sudo tar -xzf /tmp/sec-8k-ingestion.tgz -C /opt/sec-8k-ingestion
sudo chown -R $USER:$USER /opt/sec-8k-ingestion
if [[ ! -f /opt/sec-8k-ingestion/.env ]]; then
  cp /opt/sec-8k-ingestion/.env.example /opt/sec-8k-ingestion/.env
fi
cd /opt/sec-8k-ingestion
bash scripts/install_dependencies.sh
echo "Deploy complete at /opt/sec-8k-ingestion"
'

echo "Uploaded sec/ pipeline to ${GCE_INSTANCE_NAME}:/opt/sec-8k-ingestion"
