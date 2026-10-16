#!/bin/bash
# Cron wrapper on the staging API VM: pull the most recent data into PostgreSQL.
#   1. sync_recent_relational.py     raw-data-strg prices/gnews -> staging_finnhub, staging_gnews, tickers
#   2. sync_vectorized_to_postgres.py ftd-vectorized-data        -> sec_vectorized_chunks (incremental)
# SEC endpoints read ftd-vectorized-data directly, so they need no sync step.
#
# Cron has no PG* variables, so take them from the ftd-api systemd unit (the
# old prices/lakehouse_run.sh exited on a missing PGPASSWORD every night).
#
# crontab (VM is UTC; raw prices land ~22:09, gnews ~00:00):
#   20 22 * * * /home/isabellabutera/prices/sync_all_recent.sh
#   20 0  * * * /home/isabellabutera/prices/sync_all_recent.sh
set -uo pipefail
LOG_FILE="${LOG_FILE:-/home/isabellabutera/prices/sync_all_recent.log}"
PY=/home/isabellabutera/app/.venv/bin/python3

while IFS= read -r kv; do
  case "$kv" in PG*=*) export "$kv" ;; esac
done < <(systemctl show ftd-api.service -p Environment --value | tr ' ' '\n')

status=0
{
  echo "=== sync_all_recent started at $(date -u) ==="
  "$PY" /home/isabellabutera/prices/sync_recent_relational.py || { echo "relational sync FAILED"; status=1; }
  "$PY" /home/isabellabutera/app/scripts/sync_vectorized_to_postgres.py || { echo "vectorized mirror sync FAILED"; status=1; }
  echo "=== finished at $(date -u) (status=$status) ==="
} >> "$LOG_FILE" 2>&1
exit $status
