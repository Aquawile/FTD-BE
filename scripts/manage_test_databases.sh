#!/usr/bin/env bash
# Manages test databases for CI and local development
# Usage: bash scripts/manage_test_databases.sh [create-test-dbs|reset-test-dbs|drop-test-dbs]
set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${DB_VM_NAME:=ftd-postgres-vm}"
: "${DB_USER:=ftd_app}"
: "${OS_USER:=isabellabutera}"
: "${MIGRATIONS_DIR:=app/auth/migrations}"

# Test databases
TEST_DB_1="ftd_lakehouse_test"
TEST_DB_2="ftd_lakehouse_api_test"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
log() { echo "[$(date -u +%H:%M:%S)] $*"; }

run_psql() {
  local db_name="$1"
  local sql="$2"
  gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${db_name} -c \"${sql}\"" --quiet
}

run_psql_file() {
  local db_name="$1"
  local file_path="$2"
  local temp_name=$(basename "${file_path}")
  gcloud compute scp "${file_path}" "${OS_USER}@${DB_VM_NAME}:/tmp/${temp_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet
  gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${db_name} -f /tmp/${temp_name}" --quiet
}

create_database() {
  local db_name="$1"
  log "Creating database ${db_name}..."
  run_psql "postgres" "CREATE DATABASE ${db_name} OWNER ${DB_USER};"
  log "Database ${db_name} created."
}

drop_database() {
  local db_name="$1"
  log "Dropping database ${db_name}..."
  run_psql "postgres" "DROP DATABASE IF EXISTS ${db_name};"
  log "Database ${db_name} dropped."
}

apply_migrations() {
  local db_name="$1"
  log "Applying migrations to ${db_name}..."

  migration_files=()
  while IFS= read -r -d '' file; do
    migration_files+=("$file")
  done < <(find "${MIGRATIONS_DIR}" -maxdepth 1 -type f -name "[0-9][0-9][0-9]_*.sql" -print0 | sort -z)

  for migration_file in "${migration_files[@]}"; do
    migration_id=$(basename "${migration_file}" | cut -d'_' -f1)
    log "  Applying migration ${migration_id}..."
    run_psql_file "${db_name}" "${migration_file}"
  done

  log "All migrations applied to ${db_name}."
}

seed_permissions() {
  local db_name="$1"
  log "Seeding permissions in ${db_name}..."
  run_psql "${db_name}" "
    INSERT INTO permissions (name, description) VALUES
      ('tickers.search', 'Search tickers'),
      ('tickers.prices', 'View ticker prices'),
      ('tickers.news', 'View ticker news'),
      ('tickers.filings', 'View ticker filings'),
      ('tickers.timeline', 'View ticker timeline'),
      ('tickers.fiscal_year_end', 'View ticker fiscal year end'),
      ('filings.read', 'Read filing elements'),
      ('search.read', 'Execute search queries')
    ON CONFLICT (name) DO NOTHING;
  "
  log "Permissions seeded in ${db_name}."
}

grant_privileges() {
  local db_name="$1"
  log "Granting privileges in ${db_name}..."
  run_psql "${db_name}" "
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
  "
  log "Privileges granted in ${db_name}."
}

# =============================================================================
# OPERATIONS
# =============================================================================
create_test_dbs() {
  log "=== Creating Test Databases ==="

  # Check gcloud auth
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    log "WARNING: No active gcloud account. Skipping database creation."
    return 0
  fi

  for db in "${TEST_DB_1}" "${TEST_DB_2}"; do
    create_database "${db}"
    apply_migrations "${db}"
    seed_permissions "${db}"
    grant_privileges "${db}"
  done

  log "=== Test Databases Created Successfully ==="
}

reset_test_dbs() {
  log "=== Resetting Test Databases ==="

  # Check gcloud auth
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    log "WARNING: No active gcloud account. Skipping database reset."
    return 0
  fi

  for db in "${TEST_DB_1}" "${TEST_DB_2}"; do
    log "Resetting ${db}..."

    # Truncate all tables (preserving schema)
    gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${db} -c \"DO \\$\$ DECLARE r RECORD; BEGIN FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE'; END LOOP; END \\$\$;\"" --quiet

    # Reseed permissions
    seed_permissions "${db}"

    # Reset sequences
    gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${db} -c \"DO \\$\$ DECLARE r RECORD; BEGIN FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP EXECUTE 'ALTER SEQUENCE ' || quote_ident(r.sequence_name) || ' RESTART WITH 1'; END LOOP; END \\$\$;\"" --quiet
  done

  log "=== Test Databases Reset Successfully ==="
}

drop_test_dbs() {
  log "=== Dropping Test Databases ==="

  # Check gcloud auth
  if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    log "WARNING: No active gcloud account. Skipping database drop."
    return 0
  fi

  for db in "${TEST_DB_1}" "${TEST_DB_2}"; do
    drop_database "${db}"
  done

  log "=== Test Databases Dropped Successfully ==="
}

# =============================================================================
# MAIN
# =============================================================================
case "${1:-}" in
  create-test-dbs)
    create_test_dbs
    ;;
  reset-test-dbs)
    reset_test_dbs
    ;;
  drop-test-dbs)
    drop_test_dbs
    ;;
  *)
    echo "Usage: $0 [create-test-dbs|reset-test-dbs|drop-test-dbs]"
    exit 1
    ;;
esac