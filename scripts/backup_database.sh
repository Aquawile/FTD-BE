#!/bin/bash
# Logical backup of the application database to gs://ftd2026-backups/postgres/ (runs on the staging API VM).
#
#   pg_dump -Fc (custom format, compressed) streamed straight into the bucket: nothing is written to this VM's disk.
#   Every object is kept. Nothing is ever deleted or overwritten (names carry the UTC date and time).
#   After the upload it checks the object exists, is a plausible size, and that pg_restore can read its contents.
#
# Usage:
#   backup_database.sh                    take a backup now
#   backup_database.sh --if-missing-today take one only if no automatic backup exists yet for today (UTC)
#
# Cron on the API VM (UTC; the 00:20 data sync has finished by 02:30 and the SEC job starts at 03:30):
#   30 2 * * *  /home/isabellabutera/app/scripts/backup_database.sh >> /home/isabellabutera/backups/backup_database.log 2>&1
#   @reboot sleep 900 && /home/isabellabutera/app/scripts/backup_database.sh --if-missing-today >> /home/isabellabutera/backups/backup_database.log 2>&1
#
# Restore (into an empty database): gcloud storage cp <object> /tmp/x.dump && pg_restore -d <db> --no-owner --no-privileges /tmp/x.dump
set -uo pipefail

BUCKET="gs://ftd2026-backups/postgres"
PREFIX="ftd_lakehouse_staging-auto"
MIN_BYTES=$((50 * 1024 * 1024))     # a real dump is ~450 MB; anything under 50 MB is treated as a failure
STAMP="$(date -u +%Y%m%d-%H%M)"
OBJ="${BUCKET}/${PREFIX}-${STAMP}.dump"

# Cron has no PG* variables: take them from the ftd-api systemd unit (same approach as sync_all_recent.sh).
while IFS= read -r kv; do
  case "$kv" in PG*=*) export "$kv" ;; esac
done < <(systemctl show ftd-api.service -p Environment --value | tr ' ' '\n')

echo "=== backup started $(date -u) ==="

if [[ "${1:-}" == "--if-missing-today" ]]; then
  if gcloud storage ls "${BUCKET}/${PREFIX}-$(date -u +%Y%m%d)-*.dump" >/dev/null 2>&1; then
    echo "an automatic backup for today already exists; nothing to do"
    exit 0
  fi
fi

pg_dump -Fc -h "$PGHOST" -p "${PGPORT:-5432}" -U "$PGUSER" "$PGDATABASE" | gcloud storage cp - "$OBJ" --quiet
dump_status=("${PIPESTATUS[@]}")
if [[ "${dump_status[0]}" -ne 0 || "${dump_status[1]}" -ne 0 ]]; then
  echo "BACKUP FAILED: pg_dump exit ${dump_status[0]}, upload exit ${dump_status[1]}"
  exit 1
fi

size="$(gcloud storage ls -l "$OBJ" 2>/dev/null | awk 'NR==1 {print $1}')"
if [[ -z "$size" || "$size" -lt "$MIN_BYTES" ]]; then
  echo "BACKUP SUSPECT: ${OBJ} is ${size:-missing} bytes (expected at least ${MIN_BYTES})"
  exit 1
fi

# The table of contents sits at the start of a custom-format dump, so read only the first 8 MiB.
entries="$(gcloud storage cat -r 0-8388607 "$OBJ" 2>/dev/null | pg_restore --list 2>/dev/null | grep -c 'TABLE DATA')"
if [[ "${entries:-0}" -lt 10 ]]; then
  echo "BACKUP SUSPECT: pg_restore can read only ${entries:-0} table-data entries from ${OBJ}"
  exit 1
fi

echo "backup ok: ${OBJ} (${size} bytes, ${entries} tables with data)"
echo "=== backup finished $(date -u) ==="
