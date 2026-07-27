#!/bin/bash
export PGHOST=34.94.89.135
export PGPORT=5432
export PGDATABASE=ftd_lakehouse
export PGUSER=ftd_app
export PGPASSWORD='5Ou+BkyuQT3izP72219jMLy2AobRdI3f'
cd /Users/isabellabutera/gcloud-bucket-data
PYTHONPATH=/Users/isabellabutera/gcloud-bucket-data:/Users/isabellabutera/gcloud-bucket-data/sec /Users/isabellabutera/gcloud-bucket-data/.venv/bin/python3 -m lakehouse.orchestrator --postgres
