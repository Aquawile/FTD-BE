# SUBLAYER 4.1 AUDIT REPORT — EXISTING CI/CD IMPLEMENTATION

**Date:** 2026-08-24
**Auditor:** IDE Agent
**Branch:** rawdataingestion (development)
**Status:** Complete — Read-only inspection, no modifications made

---

## 1. CURRENT CI WORKFLOW ANALYSIS (`.github/workflows/ci.yml`)

### Trigger Configuration
| Property | Value |
|----------|-------|
| Push branches | `[rawdataingestion]` only |
| Pull request branches | `[rawdataingestion]` only |
| Manual dispatch | Yes (`workflow_dispatch`) |
| **Gap** | Missing `staging` branch triggers (required for Layer Three branch-to-environment mapping) |

### Job Structure
Single job `validate` running on `ubuntu-latest` with sequential steps:

| Step | Command | Pass/Fail Criteria |
|------|---------|-------------------|
| Checkout | `actions/checkout@v4` | — |
| Setup Python 3.11 | `actions/setup-python@v5` | — |
| Install Python deps | `pip install -r requirements-dev.txt` | Exit code 0 |
| Run backend tests | `python -m pytest tests/ -v` | **Fail-fast** (`continue-on-error: false`) |
| Setup Node.js 20 | `actions/setup-node@v4` with npm cache | — |
| Install frontend deps | `npm ci --prefix context/figma_prototype` | Exit code 0 |
| Build frontend | `npm run build --prefix context/figma_prototype` | **Fail-fast** (`continue-on-error: false`) |
| Upload artifact | `actions/upload-artifact@v4` | Always runs (`if: always()`) |

### Validation Stages Present
1. ✅ **Unit tests** — Runs all pytest tests (36 pass, 34 skipped locally without PostgreSQL)
2. ✅ **Frontend build** — Vite production build succeeds (3.12s, 463.58 kB JS)
3. ✅ **Artifact upload** — Frontend dist/ uploaded for 7-day retention

### Validation Stages Missing
| Missing Stage | Status | Notes |
|---------------|--------|-------|
| **Lint/Type-check** | Not configured | No ruff, flake8, mypy, or pyproject.toml in repo |
| **Integration tests (explicit)** | Implicit only | PostgreSQL tests run but skipped if DB unavailable; no separate stage |
| **Explicit stage separation** | No | All tests run in single step; no fail-fast between unit vs integration |
| **Staging branch trigger** | No | CI only triggers on `rawdataingestion` |

### Pass/Fail Criteria
- Backend tests: `continue-on-error: false` → fail-fast ✅
- Frontend build: `continue-on-error: false` → fail-fast ✅
- Overall: Single job, any step failure fails workflow ✅

### Baseline Test Results (Local, No PostgreSQL)
```
36 passed, 34 skipped, 19 warnings in 3.81s
```
- **Passed (no DB):** test_hasher, test_token, test_auth_middleware, TestUsersRouter (mocked)
- **Skipped (needs PostgreSQL):** TestUserService (19 tests), TestUserSync (5 tests), TestUsersRouterPostgres (8 tests)

---

## 2. CURRENT DEPLOY WORKFLOW ANALYSIS (`.github/workflows/deploy.yml`)

### Trigger Configuration
| Property | Value |
|----------|-------|
| Push branches | `[rawdataingestion]` only |
| Manual dispatch | Yes (`workflow_dispatch`) — **no required inputs** |
| **Gap** | Missing `staging` branch trigger; no `target_environment` input for manual dispatch |

### Job Structure
**Single job `deploy`** with conditional steps — **not split by environment**

| Component | Trigger Condition | Target |
|-----------|-------------------|--------|
| Start Price VM Cloud Function | `workflow_dispatch` OR commit msg contains `start-price-vm`/`deploy` | Cloud Functions (us-west2) |
| GNews Cloud Function | `workflow_dispatch` OR commit msg contains `gnews`/`deploy` | Cloud Functions (us-west2) |
| Prices VM Script | `workflow_dispatch` OR commit msg contains `prices`/`deploy` | data-ingest-vm (cron) |
| Application to ftd-test | `workflow_dispatch` OR commit msg contains `app`/`backend`/`frontend`/`deploy` | ftd-test VM |

### Current Deployment Behavior
- **Environment determination:** Commit message keywords, not branch name
- **CI Gate:** `Verify CI passed` step polls `gh run list` for same commit SHA — waits up to 3 min
- **Version Recording:** Echo only (`echo "Deploying revision: ${{ github.sha }}"`), no persistent `version.json`
- **Health Verification:** Only `/health` endpoint checked; no `/version` endpoint verification
- **Secrets:** `FTD_TEST_PG_PASSWORD` used for development DB only

### Target Environments
| Component | Environment | Database |
|-----------|-------------|----------|
| Application | ftd-test (development VM) | ftd_lakehouse_api_test |
| Cloud Functions | GCP Cloud Functions | N/A |
| Prices Script | data-ingest-vm | N/A |

### Gaps Against Layer Four Requirements
| Requirement | Current State | Gap |
|-------------|---------------|-----|
| Branch-gated jobs (dev vs staging) | Single job with keyword conditions | ❌ Major |
| CI gate as job dependency (`needs: ci`) | Step polling `gh run list` | ❌ Structural |
| Staging branch deployment | Not configured | ❌ Major |
| Manual dispatch with `target_environment` input | No inputs defined | ❌ Major |
| Persistent `version.json` on VM | Echo only | ❌ Major |
| `/version` endpoint verification | Not implemented | ❌ Major |
| Environment-specific DB credentials | Only `FTD_TEST_PG_PASSWORD` | ❌ Major |

---

## 3. GAP ANALYSIS SUMMARY

### Critical Gaps (Must Fix for Layer Four)

| # | Gap | Layer Four Requirement | Current State |
|---|-----|------------------------|---------------|
| 1 | CI trigger on staging branch | Match branch-to-environment mapping | CI only on `rawdataingestion` |
| 2 | Deploy split into dev/staging jobs | Mutually exclusive branch-gated jobs | Single job with keyword conditions |
| 3 | CI gate as `needs:` dependency | Structural gate, not polling step | Polling `gh run list` in deploy step |
| 4 | Manual dispatch with `target_environment` | Required input for environment selection | No inputs defined |
| 5 | Persistent `version.json` on VM | Traceability requirement | Echo only |
| 6 | `/version` endpoint verification | Deployment verification | Only `/health` checked |
| 5 | Staging DB secret (`FTD_STAGING_PG_PASSWORD`) | Staging deployment | Not configured |
| 6 | Staging VM deployment steps | Staging environment | Not present |

### Existing Strengths (Preserve)

| Strength | Description |
|----------|-------------|
| Workload Identity auth | `google-github-actions/auth@v2` with correct provider/SA |
| IAP tunneling pattern | `gcloud compute ssh --tunnel-through-iap` throughout |
| Health check polling | 24 attempts × 5s with clear logging |
| Frontend build artifact upload | Retained for potential deploy reuse |
| Cloud Functions deployment | Separate conditional steps (can remain) |
| Prices VM script deployment | Separate conditional steps (can remain) |

---

## 4. RECOMMENDED MODIFICATIONS (For Subsequent Sublayers)

### Sublayer 4.2 — CI Workflow Restructure
1. Add `staging` to push/pull_request triggers
2. Split into sequential stages (or separate jobs with `needs:`):
   - Stage 1: Lint/type-check (skip with log if not configured)
   - Stage 2: Unit tests (`pytest -k "not postgres"`)
   - Stage 3: Integration tests (`pytest -k "postgres"` — skip gracefully if DB unavailable)
   - Stage 4: Frontend build
3. All stages `continue-on-error: false` for fail-fast

### Sublayer 4.3 — Deploy Workflow Restructure
1. Split into two jobs: `deploy-development` and `deploy-staging`
2. Job-level `if:` conditions on branch (`rawdataingestion` vs `staging`)
3. Job-level `needs: ci` for structural gate
4. Job-level `environment:` for GitHub Environments UI
5. Parameterized steps via job-level `env:` (VM name, DB name, secret name)
6. `version.json` write step in each job before health check
7. Health check verifies both `/health` and `/version` (commit SHA match)
8. `workflow_dispatch` with required `target_environment` input (choice: development, staging)

### Sublayer 4.4 — Verification
1. Push to `rawdataingestion` → CI passes → deploy-development runs → `/version` on ftd-test matches
2. Push to `staging` → CI passes → deploy-staging runs → `/version` on ftd-staging matches
3. Verify no cross-deployment
4. Breaking change on feature branch → PR to rawdataingestion → CI fails → no deploy triggered

---

## 5. CONCLUSION

The existing CI/CD implementation provides a **working foundation** but requires **significant restructuring** to meet Layer Four requirements:

- **CI workflow:** Functional for development branch, needs staging trigger and explicit stage gates
- **Deploy workflow:** Functional for development via keyword conditions, needs complete restructure to branch-gated jobs with CI gate, staging support, and traceability

**No modifications made during this audit.** Ready to proceed to Sublayer 4.2 with developer approval of gap analysis.