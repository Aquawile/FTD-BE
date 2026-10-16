#!/bin/bash
# Nightly cron wrapper for sync_recent_relational.py on the staging API VM.
# Cron has no PG* variables, so take them from the ftd-api systemd unit (the
# previous prices/lakehouse_run.sh exited on a missing PGPASSWORD every night).
#
# crontab: 20 22 * * * /home/isabellabutera/prices/sync_recent_relational.sh
set -euo pipefail
LOG_FILE="${LOG_FILE:-/home/isabellabutera/prices/sync_recent_relational.log}"

while IFS= read -r kv; do
  case "$kv" in PG*=*) export "$kv" ;; esac
done < <(systemctl show ftd-api.service -p Environment --value | tr ' ' '\n')

{
  echo "=== sync_recent_relational started at $(date -u) ==="
  /home/isabellabutera/app/.venv/bin/python3 /home/isabellabutera/prices/sync_recent_relational.py
  echo "=== finished at $(date -u) ==="
} >> "$LOG_FILE" 2>&1
