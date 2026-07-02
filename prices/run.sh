#!/bin/bash
cd ~/gcloud-bucket-data/prices
pip3 install -r requirements.txt >> /tmp/prices.log 2>&1
python3 main.py >> /tmp/prices.log 2>&1
EXIT_CODE=$?
echo "Pipeline finished at $(date -u) with exit code $EXIT_CODE" >> /tmp/prices.log
gcloud compute instances stop data-ingest-vm --zone=us-west2-a --project=ftd2026 --quiet >> /tmp/prices.log 2>&1
echo "VM stopped after pipeline completion" >> /tmp/prices.log
exit $EXIT_CODE
