#!/bin/bash
source ~/prices-ingestion/.venv/bin/activate
cd ~/prices-ingestion
pip install -r requirements.txt >> /tmp/prices-ingestion.log 2>&1
python3 main.py >> /tmp/prices-ingestion.log 2>&1
EXIT_CODE=$?
echo "Pipeline finished at $(date -u) with exit code $EXIT_CODE" >> /tmp/prices-ingestion.log
gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet >> /tmp/prices-ingestion.log 2>&1
echo "VM stopped after pipeline completion" >> /tmp/prices-ingestion.log
exit $EXIT_CODE
