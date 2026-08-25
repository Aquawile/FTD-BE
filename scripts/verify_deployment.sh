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
API_PORT=8000

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

# Run a check and track result
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
        return 1
    fi

    if [[ -n "${expected}" ]] && ! echo "${output}" | grep -q "${expected}"; then
        error "FAIL: ${check_name} - Expected pattern '${expected}' not found"
        error "Actual output: ${output}"
        FAILED_CHECKS+=("${check_name}: Expected '${expected}', got '${output}'")
        return 1
    fi

    log "PASS: ${check_name}"
    PASSED_CHECKS+=("${check_name}")
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

# 2. Web health endpoint
run_check "Web health endpoint" \
    "curl -s http://127.0.0.1:${WEB_PORT}/health" \
    "healthy" \
    "${WEB_VM}"

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

# 5. Backend health endpoint
run_check "Backend health endpoint" \
    "curl -s http://127.0.0.1:${API_PORT}/health" \
    '"status":"ok"' \
    "${API_VM}"

# 6. Backend version endpoint
run_check "Backend version endpoint" \
    "curl -s http://127.0.0.1:${API_PORT}/version" \
    "${EXPECTED_COMMIT}" \
    "${API_VM}"

# 7. Version metadata file on API VM
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

# 9. Cross-deployment check: other environment unchanged
OTHER_EXPECTED_COMMIT=""
if [[ "${OTHER_ENV}" == "development" ]]; then
    # For development, we need to get current deployed commit from dev VM
    OTHER_EXPECTED_COMMIT=$(ssh_cmd "${OTHER_API_VM}" "cat /home/${OS_USER}/version.json 2>/dev/null | grep -o '\"commit_sha\":\"[^\"]*\"' | cut -d'\"' -f4" || echo "")
    if [[ -n "${OTHER_EXPECTED_COMMIT}" ]] && [[ "${OTHER_EXPECTED_COMMIT}" != "${EXPECTED_COMMIT}" ]]; then
        log "Cross-deployment check: ${OTHER_ENV} at ${OTHER_EXPECTED_COMMIT} (expected different from ${EXPECTED_COMMIT})"
        PASSED_CHECKS+=("Cross-deployment check: ${OTHER_ENV} unchanged")
    else
        error "FAIL: Cross-deployment check - could not verify ${OTHER_ENV} version"
        FAILED_CHECKS+=("Cross-deployment check: Could not verify ${OTHER_ENV}")
    fi
else
    # For staging, check dev VM
    OTHER_EXPECTED_COMMIT=$(ssh_cmd "${OTHER_API_VM}" "cat /home/${OS_USER}/version.json 2>/dev/null | grep -o '\"commit_sha\":\"[^\"]*\"' | cut -d'\"' -f4" || echo "")
    if [[ -n "${OTHER_EXPECTED_COMMIT}" ]] && [[ "${OTHER_EXPECTED_COMMIT}" != "${EXPECTED_COMMIT}" ]]; then
        log "Cross-deployment check: ${OTHER_ENV} at ${OTHER_EXPECTED_COMMIT} (expected different from ${EXPECTED_COMMIT})"
        PASSED_CHECKS+=("Cross-deployment check: ${OTHER_ENV} unchanged")
    else
        error "FAIL: Cross-deployment check - could not verify ${OTHER_ENV} version"
        FAILED_CHECKS+=("Cross-deployment check: Could not verify ${OTHER_ENV}")
    fi
fi

# 10. Database connectivity from API VM
run_check "Database connectivity" \
    "PGPASSWORD='5Ou+BkyuQT3izP72219jMLy2AobRdI3f' psql -h 10.168.0.3 -U ftd_app -d ftd_lakehouse_staging -c 'SELECT 1' 2>/dev/null || PGPASSWORD='5Ou+BkyuQT3izP72219jMLy2AobRdI3f' psql -h 10.168.0.3 -U ftd_app -d ftd_lakehouse_api_test -c 'SELECT 1' 2>/dev/null" \
    "1 row" \
    "${API_VM}"

# =============================================================================
# SUMMARY
# =============================================================================
log ""
log "=== Verification Summary ==="
log "Environment: ${ENVIRONMENT}"
log "Expected commit: ${EXPECTED_COMMIT}"
log "Passed: ${#PASSED_CHECKS[@]}"
log "Failed: ${#FAILED_CHECKS[@]}"

for check in "${PASSED_CHECKS[@]}"; do
    log "  ✓ ${check}"
done

for check in "${FAILED_CHECKS[@]}"; do
    error "  ✗ ${check}"
done

if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
    error "=== VERIFICATION FAILED ==="
    exit 1
fi

log "=== ALL CHECKS PASSED ==="
exit 0