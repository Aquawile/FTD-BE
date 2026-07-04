#!/bin/bash
trap 'gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet >> /tmp/prices.log 2>&1; echo "VM stopped via trap (exit $?)" >> /tmp/prices.log' EXIT

cd ~/prices
pip3 install --break-system-packages -r requirements.txt >> /tmp/prices.log 2>&1
python3 main.py >> /tmp/prices.log 2>&1
EXIT_CODE=$?
echo "Pipeline finished at $(date -u) with exit code $EXIT_CODE" >> /tmp/prices.log
exit $EXIT_CODE
