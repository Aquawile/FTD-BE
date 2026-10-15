#!/usr/bin/env bash
# Applies pending database migrations to the staging database (ftd_lakehouse_staging)
# on ftd-postgres-vm. Idempotent - safe to run multiple times.
# Usage: bash scripts/apply_staging_migrations.sh
set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${DB_VM_NAME:=ftd-postgres-vm}"
: "${DB_NAME:=ftd_lakehouse_staging}"
: "${DB_USER:=ftd_app}"
: "${OS_USER:=isabellabutera}"
: "${MIGRATIONS_DIR:=app/auth/migrations}"

# Migration tracking table name
TRACKING_TABLE="schema_migrations"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
log() { echo "[$(date -u +%H:%M:%S)] $*"; }

run_psql() {
  local sql="$1"
  gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${DB_NAME} -c \"${sql}\"" --quiet
}

run_psql_file() {
  local file_path="$1"
  local temp_name=$(basename "${file_path}")
  local max_attempts=3
  local attempt=1
  
  while [[ ${attempt} -le ${max_attempts} ]]; do
    if gcloud compute scp "${file_path}" "${OS_USER}@${DB_VM_NAME}:/tmp/${temp_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet; then
      gcloud compute ssh "${OS_USER}@${DB_VM_NAME}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="sudo -u postgres psql -d ${DB_NAME} -f /tmp/${temp_name}" --quiet
      return 0
    fi
    log "SCP attempt ${attempt}/${max_attempts} failed for ${file_path}, retrying in 5s..."
    sleep 5
    ((attempt++))
  done
  log "ERROR: Failed to copy ${file_path} after ${max_attempts} attempts"
  return 1
}

# Check if a migration's effects are already present in the database schema
check_migration_applied() {
  local mig_id="$1"
  
  case "${mig_id}" in
    "001")
      # Tables: users, permissions, user_permissions, user_permissions_index
      run_psql "SELECT to_regclass('public.users');" 2>/dev/null | grep -q "users" && return 0
      ;;
    "002")
      # Indexes on user_permissions_index
      run_psql "SELECT to_regclass('public.user_permissions_index');" 2>/dev/null | grep -q "user_permissions_index" && return 0
      ;;
    "003")
      # Composite index
      run_psql "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_permissions_index_composite';" 2>/dev/null | grep -q "1" && return 0
      ;;
    "004")
      # firebase_uid, updated_at columns on users table
      run_psql "SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='firebase_uid';" 2>/dev/null | grep -q "1" && return 0
      ;;
    "005")
      # password_hash nullable
      run_psql "SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='password_hash' AND is_nullable='YES';" 2>/dev/null | grep -q "1" && return 0
      ;;
    "007")
      # api_usage_log table created (audit logging)
      run_psql "SELECT to_regclass('public.api_usage_log');" 2>/dev/null | grep -q "api_usage_log" && return 0
      ;;
    "008")
      # staging_sec and unified_staging renamed to _archive
      run_psql "SELECT to_regclass('public.staging_sec_archive')" 2>/dev/null | grep -q "staging_sec_archive" && return 0
      ;;
    "009")
      # sec_vectorized_chunks table created for GCS vector data sync
      run_psql "SELECT to_regclass('public.sec_vectorized_chunks');" 2>/dev/null | grep -q "sec_vectorized_chunks" && return 0
      ;;
    *)
      # For future migrations, check tracking table only
      result=$(run_psql "SELECT success FROM ${TRACKING_TABLE} WHERE migration_id = '${mig_id}';" 2>/dev/null | tail -3 | head -1 | xargs || echo "")
      if [[ "${result}" == "t" || "${result}" == "true" ]]; then
        return 0
      fi
      ;;
  esac
  return 1
}

# Mark migration as applied in tracking table (success)
mark_migration_success() {
  local mig_id="$1"
  run_psql "
    INSERT INTO ${TRACKING_TABLE} (migration_id, applied_at, success)
    VALUES ('${mig_id}', NOW(), TRUE)
    ON CONFLICT (migration_id) DO UPDATE SET applied_at = NOW(), success = TRUE;
  "
}

# Mark migration as failed in tracking table
mark_migration_failed() {
  local mig_id="$1"
  run_psql "
    INSERT INTO ${TRACKING_TABLE} (migration_id, applied_at, success)
    VALUES ('${mig_id}', NOW(), FALSE)
    ON CONFLICT (migration_id) DO UPDATE SET applied_at = NOW(), success = FALSE;
  "
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
log "=== Applying Staging Database Migrations ==="
log "Project: ${GCP_PROJECT}"
log "Database VM: ${DB_VM_NAME}"
log "Database: ${DB_NAME}"
log "Migrations directory: ${MIGRATIONS_DIR}"
log ""

# Ensure migration tracking table exists
log "Ensuring migration tracking table exists..."
run_psql "
CREATE TABLE IF NOT EXISTS ${TRACKING_TABLE} (
    migration_id VARCHAR(10) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL DEFAULT TRUE
);
"

# Discover migration files
migration_files=()
while IFS= read -r -d '' file; do
  migration_files+=("$file")
done < <(find "${MIGRATIONS_DIR}" -maxdepth 1 -type f -name "[0-9][0-9][0-9]_*.sql" -print0 | sort -z)
if [[ ${#migration_files[@]} -eq 0 ]]; then
  log "No migration files found in ${MIGRATIONS_DIR}"
  exit 0
fi

log "Found ${#migration_files[@]} migration file(s):"
for f in "${migration_files[@]}"; do log "  ${f}"; done
log ""

# Apply each migration
for migration_file in "${migration_files[@]}"; do
  migration_id=$(basename "${migration_file}" | cut -d'_' -f1)
  
  # Check if already applied (schema-based for initial migrations, tracking table for others)
  if check_migration_applied "${migration_id}"; then
    log "Migration ${migration_id} already applied (schema verified), marking as success in tracking table."
    mark_migration_success "${migration_id}"
    continue
  fi
  
  log "Migration ${migration_id} not yet applied. Applying..."
  
  # Record attempt (mark as pending/failed initially)
  mark_migration_failed "${migration_id}"
  
  # Apply the migration with retry
  if run_psql_file "${migration_file}"; then
    # Mark as successful
    mark_migration_success "${migration_id}"
    log "Migration ${migration_id} applied successfully."
  else
    log "ERROR: Migration ${migration_id} failed!"
    exit 1
  fi
done

log ""
log "=== All Migrations Applied Successfully ==="
log "Final migration status:"
run_psql "SELECT migration_id, applied_at, success FROM ${TRACKING_TABLE} ORDER BY migration_id;"