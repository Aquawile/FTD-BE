#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/lakehouse-pipeline.log"
PGHOST="10.168.0.3"
PGDATABASE="ftd_lakehouse_staging"
PGUSER="ftd_app"
PGPASSWORD="5Ou+BkyuQT3izP72219jMLy2AobRdI3f"
PGPORT="5432"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Starting lakehouse pipeline" | tee -a "$LOG_FILE"

cd /home/isabellabutera/app

if [ ! -d "lakehouse" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Syncing lakehouse code..." | tee -a "$LOG_FILE"
    gcloud compute scp --tunnel-through-iap --recurse isabellabutera@ftd-staging-api:/home/isabellabutera/app/lakehouse /home/isabellabutera/app/lakehouse --zone=us-west2-a --project=ftd2026 --quiet
fi

if [ ! -d "sec" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Syncing sec code..." | tee -a "$LOG_FILE"
    gcloud compute scp --tunnel-through-iap --recurse isabellabutera@ftd-staging-api:/home/isabellabutera/app/sec /home/isabellabutera/app/sec --zone=us-west2-a --project=ftd2026 --quiet
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Installing dependencies..." | tee -a "$LOG_FILE"
/home/isabellabutera/app/.venv/bin/pip install beautifulsoup4 lxml python-dotenv psycopg2-binary 2>&1 | tee -a "$LOG_FILE"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Running lakehouse orchestrator with PostgreSQL output..." | tee -a "$LOG_FILE"
PYTHONPATH=/home/isabellabutera/app/sec \
PGHOST="$PGHOST" \
PGPORT="$PGPORT" \
PGDATABASE="$PGDATABASE" \
PGUSER="$PGUSER" \
PGPASSWORD="$PGPASSWORD" \
/home/isabellabutera/app/.venv/bin/python -m lakehouse.orchestrator --postgres 2>&1 | tee -a "$LOG_FILE"

LAKEHOUSE_EXIT=$?
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Lakehouse pipeline completed with exit code $LAKEHOUSE_EXIT" | tee -a "$LOG_FILE"

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Stopping VM..." | tee -a "$LOG_FILE"
gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Pipeline complete" | tee -a "$LOG_FILE"
exit $LAKEHOUSE_EXIT
