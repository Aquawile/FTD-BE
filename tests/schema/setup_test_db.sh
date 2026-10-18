#!/usr/bin/env bash
# Build a throwaway Postgres for the db_integration tests, shaped like staging.
#
#   1. roles: ftd_app (the API's login role) with a throwaway password
#   2. database: the staging structure (tests/schema/staging_schema.sql), with
#      staging's owners and grants, and no data
#   3. migrations: 001-011 are already in that structure, so they're recorded in
#      schema_migrations; any newer app/auth/migrations/NNN_*.sql is applied the
#      way deploy.yml does it (one transaction, ON_ERROR_STOP, ledger row)
#   4. seed: tests/schema/seed.sql (a few tickers, quotes, news, filings, users)
#
# Only ever point this at a disposable server (the CI service container). It
# refuses to touch ftd_lakehouse_staging.
#
# Env: PGHOST, PGPORT, PGUSER (superuser), PGPASSWORD; TEST_DB (default
# ftd_lakehouse_test); FTD_APP_PASSWORD (default ftd_app_test).
set -euo pipefail

cd "$(dirname "$0")/../.."
TEST_DB="${TEST_DB:-ftd_lakehouse_test}"
FTD_APP_PASSWORD="${FTD_APP_PASSWORD:-ftd_app_test}"

if [[ "$TEST_DB" == "ftd_lakehouse_staging" ]]; then
  echo "refusing to build test data in ftd_lakehouse_staging" >&2
  exit 1
fi

PSQL=(psql -v ON_ERROR_STOP=1 -X -q)

"${PSQL[@]}" -d postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ftd_app') THEN
    CREATE ROLE ftd_app LOGIN PASSWORD '${FTD_APP_PASSWORD}';
  END IF;
END \$\$;
SQL
"${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB}" -c "CREATE DATABASE ${TEST_DB} OWNER ftd_app"

echo "schema: tests/schema/staging_schema.sql"
"${PSQL[@]}" -d "$TEST_DB" -f tests/schema/staging_schema.sql

"${PSQL[@]}" -d "$TEST_DB" -c "INSERT INTO schema_migrations (migration_id)
  SELECT to_char(n, 'FM000') FROM generate_series(1, 11) n ON CONFLICT DO NOTHING"

for f in app/auth/migrations/[0-9][0-9][0-9]_*.sql; do
  id="$(basename "$f" | cut -c1-3)"
  applied="$("${PSQL[@]}" -d "$TEST_DB" -Atc "SELECT 1 FROM schema_migrations WHERE migration_id = '$id' AND success")"
  [[ -n "$applied" ]] && continue
  echo "migration $id: $f"
  "${PSQL[@]}" -d "$TEST_DB" --single-transaction -f "$f" \
    -c "INSERT INTO schema_migrations (migration_id) VALUES ('$id')"
done

echo "seed: tests/schema/seed.sql"
"${PSQL[@]}" -d "$TEST_DB" -f tests/schema/seed.sql
"${PSQL[@]}" -d "$TEST_DB" -Atc "SELECT 'tickers=' || (SELECT COUNT(*) FROM tickers) || ' quotes=' || (SELECT COUNT(*) FROM staging_finnhub) || ' news=' || (SELECT COUNT(*) FROM staging_gnews) || ' chunks=' || (SELECT COUNT(*) FROM sec_vectorized_chunks)"
