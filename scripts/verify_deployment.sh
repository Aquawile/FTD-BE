#!/usr/bin/env bash
# Post-deployment verification script
# Usage: bash scripts/verify_deployment.sh <environment> <expected_commit_sha>
# Environment: development | staging
# Exit code: 0 = all checks pass, 1 = any check fails, 2 = infrastructure error
set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
: "${GCP_PROJECT:=ftd2026}"
: "${GCE_ZONE:=us-west2-a}"
: "${OS_USER:=isabellabutera}"

# VM names by environment
DEV_VM="ftd-test"
STAGING_WEB_VM="ftd-staging-web"
STAGING_API_VM="ftd-staging-api"
PROD_VM="ftd-prod"  # Not used yet

# Ports
WEB_PORT=8080
API_PORT=8080

# JSON results tracking
CHECK_RESULTS=()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
log() { echo "[$(date -u +%H:%M:%S)] $*"; }

error() { echo "[$(date -u +%H:%M:%S)] ERROR: $*" >&2; }

infrastructure_error() {
    error "INFRASTRUCTURE ERROR: $*"
    exit 2
}

check_gcloud_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
        infrastructure_error "No active gcloud account. Run 'gcloud auth login'."
    fi
}

ssh_cmd() {
    local vm_name="$1"
    local cmd="$2"
    gcloud compute ssh "${OS_USER}@${vm_name}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --tunnel-through-iap --command="${cmd}" --quiet
}

scp_cmd() {
    local src="$1"
    local dst="$2"
    gcloud compute scp --tunnel-through-iap "${src}" "${OS_USER}@${dst}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --quiet
}

# JSON output for verification results
CHECK_RESULTS=()

# Results are built with jq so command output (HTML, quotes, newlines) can't break the JSON.
# status: passed | failed | skipped. "actual" is capped at 500 characters.
add_check_result() {
    local name="$1"
    local status="$2"
    local expected="$3"
    local actual="${4:0:500}"
    CHECK_RESULTS+=("$(jq -cn --arg name "${name}" --arg status "${status}" --arg expected "${expected}" --arg actual "${actual}" \
        '{name: $name, status: $status, passed: ($status == "passed"), expected: $expected, actual: $actual}')")
}

write_json_results() {
    if [[ ${#CHECK_RESULTS[@]} -eq 0 ]]; then
        echo "" | jq -s --arg env "${ENVIRONMENT}" --arg commit "${EXPECTED_COMMIT}" \
            '{environment: $env, expected_commit: $commit, checks: []}' > verification-results.json
        return
    fi
    printf '%s\n' "${CHECK_RESULTS[@]}" | jq -s --arg env "${ENVIRONMENT}" --arg commit "${EXPECTED_COMMIT}" \
        '{environment: $env, expected_commit: $commit,
          summary: {passed: map(select(.status == "passed")) | length,
                    failed: map(select(.status == "failed")) | length,
                    skipped: map(select(.status == "skipped")) | length},
          checks: .}' > verification-results.json
}

run_check() {
    local check_name="$1"
    local cmd="$2"
    local expected="$3"
    local vm_name="$4"

    log "Running check: ${check_name} on ${vm_name}..."

    local output
    if ! output=$(ssh_cmd "${vm_name}" "${cmd}" 2>&1); then
        error "FAIL: ${check_name} - SSH command failed"
        error "Output: ${output}"
        FAILED_CHECKS+=("${check_name}: SSH failed")
        add_check_result "${check_name}" "failed" "${expected}" "${output}"
        return 0
    fi

    if [[ -n "${expected}" ]] && ! echo "${output}" | grep -q "${expected}"; then
        error "FAIL: ${check_name} - Expected pattern '${expected}' not found"
        error "Actual output: ${output}"
        FAILED_CHECKS+=("${check_name}: Expected '${expected}', got '${output}'")
        add_check_result "${check_name}" "failed" "${expected}" "${output}"
        return 0
    fi

    log "PASS: ${check_name}"
    PASSED_CHECKS+=("${check_name}")
    add_check_result "${check_name}" "passed" "${expected}" "${output}"
    return 0
}

# =============================================================================
# MAIN VERIFICATION LOGIC
# =============================================================================
ENVIRONMENT="${1:-}"
EXPECTED_COMMIT="${2:-}"

if [[ -z "${ENVIRONMENT}" ]] || [[ -z "${EXPECTED_COMMIT}" ]]; then
    echo "Usage: $0 <environment> <expected_commit_sha>"
    echo "Environment: development | staging"
    exit 1
fi

if [[ "${ENVIRONMENT}" != "development" ]] && [[ "${ENVIRONMENT}" != "staging" ]]; then
    error "Invalid environment: ${ENVIRONMENT}. Must be 'development' or 'staging'."
    exit 1
fi

# Set VM names based on environment
if [[ "${ENVIRONMENT}" == "development" ]]; then
    WEB_VM="${DEV_VM}"
    API_VM="${DEV_VM}"
    OTHER_ENV="staging"
    OTHER_WEB_VM="${STAGING_WEB_VM}"
    OTHER_API_VM="${STAGING_API_VM}"
else
    WEB_VM="${STAGING_WEB_VM}"
    API_VM="${STAGING_API_VM}"
    OTHER_ENV="development"
    OTHER_WEB_VM="${DEV_VM}"
    OTHER_API_VM="${DEV_VM}"
fi

# Initialize tracking arrays
PASSED_CHECKS=()
FAILED_CHECKS=()
SKIPPED_CHECKS=()

log "=== Post-Deployment Verification ==="
log "Environment: ${ENVIRONMENT}"
log "Expected commit: ${EXPECTED_COMMIT}"
log "Web VM: ${WEB_VM}"
log "API VM: ${API_VM}"
log ""

# Check gcloud auth
check_gcloud_auth

# =============================================================================
# VERIFICATION CHECKS
# =============================================================================

# 1. Frontend served (staging only - development doesn't have separate web VM)
if [[ "${ENVIRONMENT}" == "staging" ]]; then
    run_check "Frontend served" \
        "curl -s http://127.0.0.1:${WEB_PORT}/ | grep -q '<html'" \
        "" \
        "${WEB_VM}"
fi

# 2. Web health endpoint (staging only)
if [[ "${ENVIRONMENT}" == "staging" ]]; then
    run_check "Web health endpoint" \
        "curl -s http://127.0.0.1:${WEB_PORT}/health" \
        "healthy" \
        "${WEB_VM}"
fi

# 3. API proxy health (staging only - development doesn't have proxy)
if [[ "${ENVIRONMENT}" == "staging" ]]; then
    run_check "API proxy health (/api/health)" \
        "curl -s http://127.0.0.1:${WEB_PORT}/api/health" \
        '"status":"ok"' \
        "${WEB_VM}"
fi

# 4. API version via proxy (staging only)
if [[ "${ENVIRONMENT}" == "staging" ]]; then
    run_check "API version via proxy (/api/version)" \
        "curl -s http://127.0.0.1:${WEB_PORT}/api/version" \
        "${EXPECTED_COMMIT}" \
        "${WEB_VM}"
fi

# 5. Backend health endpoint (both environments)
run_check "Backend health endpoint" \
    "curl -s http://127.0.0.1:${API_PORT}/health" \
    '"status":"ok"' \
    "${API_VM}"

# 6. Backend version endpoint (both environments)
run_check "Backend version endpoint" \
    "curl -s http://127.0.0.1:${API_PORT}/version" \
    "${EXPECTED_COMMIT}" \
    "${API_VM}"

# 7. Version metadata file on API VM (both environments)
run_check "Version metadata file (API VM)" \
    "cat /home/${OS_USER}/version.json | grep -q '${EXPECTED_COMMIT}'" \
    "" \
    "${API_VM}"

# 8. Version metadata file on Web VM (staging only)
if [[ "${ENVIRONMENT}" == "staging" ]]; then
    run_check "Version metadata file (Web VM)" \
        "cat /home/${OS_USER}/version.json | grep -q '${EXPECTED_COMMIT}'" \
        "" \
        "${WEB_VM}"
fi

# 9. Cross-deployment check: other environment unchanged.
# Skipped (not failed) when the other environment's VM exists but isn't RUNNING
# (e.g. ftd-test is TERMINATED): there is nothing deployed there to compare.
OTHER_VM_STATUS=$(gcloud compute instances describe "${OTHER_API_VM}" --zone="${GCE_ZONE}" --project="${GCP_PROJECT}" --format='value(status)' 2>/dev/null || echo "")
if [[ -n "${OTHER_VM_STATUS}" ]] && [[ "${OTHER_VM_STATUS}" != "RUNNING" ]]; then
    log "SKIP: Cross-deployment check - ${OTHER_ENV} VM ${OTHER_API_VM} is ${OTHER_VM_STATUS}"
    SKIPPED_CHECKS+=("Cross-deployment check: ${OTHER_ENV} VM ${OTHER_API_VM} is ${OTHER_VM_STATUS}")
    add_check_result "Cross-deployment check" "skipped" "${OTHER_ENV} unchanged" "${OTHER_API_VM} is ${OTHER_VM_STATUS}"
else
    OTHER_EXPECTED_COMMIT=$(ssh_cmd "${OTHER_API_VM}" "python3 -c \"import json, sys; print(json.load(open('/home/isabellabutera/version.json'))['commit_sha'])\"" 2>/dev/null || echo "")
    if [[ -n "${OTHER_EXPECTED_COMMIT}" ]] && [[ "${OTHER_EXPECTED_COMMIT}" != "${EXPECTED_COMMIT}" ]]; then
        log "Cross-deployment check: ${OTHER_ENV} at ${OTHER_EXPECTED_COMMIT} (expected different from ${EXPECTED_COMMIT})"
        PASSED_CHECKS+=("Cross-deployment check: ${OTHER_ENV} unchanged")
        add_check_result "Cross-deployment check" "passed" "${OTHER_ENV} unchanged" "${OTHER_EXPECTED_COMMIT}"
    else
        error "FAIL: Cross-deployment check - could not verify ${OTHER_ENV} version (VM status: ${OTHER_VM_STATUS:-unknown})"
        FAILED_CHECKS+=("Cross-deployment check: Could not verify ${OTHER_ENV}")
        add_check_result "Cross-deployment check" "failed" "${OTHER_ENV} unchanged" "${OTHER_EXPECTED_COMMIT}"
    fi
fi

# 10. Database connectivity from the API VM, using the ftd-api service's own PG* settings
# (no credentials in this script).
DB_CHECK_CMD='while IFS= read -r kv; do case "$kv" in PG*=*) export "$kv" ;; esac; done < <(systemctl show ftd-api.service -p Environment --value | tr " " "\n"); psql -At -c "SELECT '"'"'db_ok'"'"'"'
run_check "Database connectivity" "${DB_CHECK_CMD}" "db_ok" "${API_VM}"

# =============================================================================
# SUMMARY
# =============================================================================
log ""
log "=== Verification Summary ==="
log "Environment: ${ENVIRONMENT}"
log "Expected commit: ${EXPECTED_COMMIT}"
log "Passed: ${#PASSED_CHECKS[@]}"
log "Failed: ${#FAILED_CHECKS[@]}"
log "Skipped: ${#SKIPPED_CHECKS[@]}"

if [[ ${#PASSED_CHECKS[@]} -gt 0 ]]; then
    for check in "${PASSED_CHECKS[@]}"; do
        log "  ✓ ${check}"
    done
fi

if [[ ${#SKIPPED_CHECKS[@]} -gt 0 ]]; then
    for check in "${SKIPPED_CHECKS[@]}"; do
        log "  - skipped: ${check}"
    done
fi

if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
    for check in "${FAILED_CHECKS[@]}"; do
        error "  ✗ ${check}"
    done
fi

# Write JSON results for artifact upload
write_json_results

if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
    error "=== VERIFICATION FAILED ==="
    exit 1
fi

log "=== ALL CHECKS PASSED ==="
exit 0