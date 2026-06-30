#!/bin/bash
source ~/prices-ingestion/.venv/bin/activate
cd ~/prices-ingestion
python3 main.py >> /tmp/prices-ingestion.log 2>&1
echo "Pipeline finished at $(date -u)" >> /tmp/prices-ingestion.log
# Remove this cron job so it doesn't run again
(crontab -l 2>/dev/null | grep -v 'prices-ingestion/run.sh') | crontab -
# Stop the VM after successful completion
gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet >> /tmp/prices-ingestion.log 2>&1
echo "VM stopped after pipeline completion" >> /tmp/prices-ingestion.log
