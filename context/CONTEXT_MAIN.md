# COMPLETE AGENT REFERENCE — FTD PROJECT
*Everything an agent needs to not rediscover solved problems. Save this locally.*

---

## 1. PROJECT IDENTITY & REPOSITORY

| Property | Value |
|----------|-------|
| **Project** | Finance Tracker Dashboard (FTD) — data ingestion monorepo + backend API + React frontend |
| **GCP Project** | `ftd2026` |
| **Primary Bucket** | `raw-data-strg` (raw ingestion) |
| **Processed Bucket** | `processed-layer-one` (lakehouse Parquet output) |
| **Main Branch** | `rawdataingestion` (all development) |
| **Protected Branch** | `main` (manual only, never push directly) |
| **Working Directory** | `/Users/isabellabutera/gcloud-bucket-data` |

---

## 2. TWO INDEPENDENT INITIATIVES (CRITICAL DISTINCTION)

### Initiative A: Firebase/App Foundation (COMPLETED)
- **Prompt source**: `context/layers-prompts/` (immutable, do not modify)
- **What it built**: Entire application stack — Firebase Auth → PostgreSQL User Model → Database Access Boundary → Service Layer → FastAPI API → React Integration
- **Documented in**: `context/MEMORY.md` sections 25-60
- **Status**: COMPLETE. Vertical slice working: Firebase Login → Real API → Real PostgreSQL User → Real Profile

### Initiative B: Dev/Staging Formalization (ACTIVE — YOUR CURRENT WORK)
- **Prompt source**: `context/maintenance-prof/` (immutable, do not modify)
- **What it formalizes**: Development environment, deployment automation, database access reproducibility, staging
- **High-level layers** (from `context/maintenance-prof/high-level-layers.md`):
  1. **Layer 1** — Development Deployment Pipeline (COMPLETED)
  2. **Layer 2** — Controlled PostgreSQL Data Access & Backend Application Interface (ACTIVE — at Sublayer 2.5)
  3. **Layer 3** — Application Service Layer & Business Logic (PLANNED)
  4. **Layer 4** — FastAPI API Endpoints (PLANNED)
  5. **Layer 5** — (empty)

**NEVER conflate layer numbers between initiatives.** Always prefix: `maintenance-prof Layer 2.5` vs `layers-prompts Layer 2`.

---

## 3. INFRASTRUCTURE — VMS & NETWORK

### VM: `ftd-test` (Development Application Server)
| Property | Value |
|----------|-------|
| **Zone** | `us-west2-a` |
| **Internal IP** | `10.168.0.4` |
| **External IP** | Changes on stop/start (currently `34.94.193.132`) |
| **OS User** | `isabellabutera` |
| **Python** | 3.13.5 |
| **Node.js** | NOT installed (frontend built locally, deployed as static assets) |
| **FastAPI** | Bound to `127.0.0.1:8000` (LOOPBACK ONLY — never `0.0.0.0`) |
| **Process Management** | `nohup` + `start_app.sh` (no systemd) |
| **Logs** | `/tmp/uvicorn.log` |
| **Access** | **IAP/SSH tunneling ONLY** — no public exposure |
| **SSH Command** | `gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap` |
| **IAP Tunnel to API** | `gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap -- -L 18000:127.0.0.1:8000` → then `http://localhost:18000` |

### VM: `ftd-staging-web` (Staging Web Server — React + nginx)
| Property | Value |
|----------|-------|
| **Zone** | `us-west2-a` |
| **Internal IP** | `10.168.0.6` |
| **External IP** | `34.20.174.125` |
| **Machine Type** | `e2-medium` |
| **OS User** | `isabellabutera` |
| **Services** | nginx on port 8080 (serves React `dist/`, proxies `/api/*` → `10.168.0.7:8000`) |
| **Access** | **IAP/SSH tunneling ONLY** (tags: `http-server,https-server` for IAP firewall) |
| **SSH Command** | `gcloud compute ssh ftd-staging-web --zone=us-west2-a --project=ftd2026 --tunnel-through-iap` |

### VM: `ftd-staging-api` (Staging Backend Server — FastAPI)
| Property | Value |
|----------|-------|
| **Zone** | `us-west2-a` |
| **Internal IP** | `10.168.0.7` |
| **External IP** | `35.236.101.6` |
| **Machine Type** | `e2-medium` |
| **OS User** | `isabellabutera` |
| **FastAPI** | Bound to `0.0.0.0:8000` (internal VPC only — NOT public) |
| **Process Management** | `nohup` + `start_app.sh` with `HOST=0.0.0.0` |
| **Logs** | `/tmp/uvicorn.log` |
| **Access** | **IAP/SSH tunneling ONLY** (tags: `http-server,https-server` for IAP firewall) |
| **SSH Command** | `gcloud compute ssh ftd-staging-api --zone=us-west2-a --project=ftd2026 --tunnel-through-iap` |
| **DB Connection** | Internal VPC to `ftd-postgres-vm` at `10.168.0.3:5432` |

### VM: `ftd-postgres-vm` (PostgreSQL Database Server)
| Property | Value |
|----------|-------|
| **Zone** | `us-west2-a` |
| **Internal IP** | `10.168.0.3` (STABLE — use this) |
| **External IP** | Changes on stop/start (currently `34.94.216.101`) |
| **PostgreSQL** | 15.18, listening on `127.0.0.1:5432` (INTERNAL ONLY) |
| **OS User** | `isabellabutera` |
| **Access** | **IAP/SSH tunneling ONLY** — no public PostgreSQL exposure |
| **SSH Command** | `gcloud compute ssh ftd-postgres-vm --zone=us-west2-a --project=ftd2026 --tunnel-through-iap` |
| **IAP Tunnel to PostgreSQL** | `gcloud compute start-iap-tunnel ftd-postgres-vm 5432 --zone=us-west2-a --project=ftd2026 --local-host-port=127.0.0.1:5432` |
| **Known Issue** | After VM restart: SSH daemon fails banner exchange, network interface `ens4` may fail DHCP. **Fix**: Resize VM (e2-micro → e2-medium) or use Serial Console to restart networking. |

### VM: `data-ingest-vm` (Ingestion Pipeline Runner)
| Property | Value |
|----------|-------|
| **Zone** | `us-west2-a` |
| **Purpose** | Runs SEC 8-K pipeline (Cloud Scheduler 03:30 UTC) and Finnhub prices (cron 22:00) |
| **Startup Script** | Sources `.env`, runs `python -m src.main`, stops itself in `finally` block |
| **Shared with** | SEC and prices pipelines both stop this VM when done |

### Network & Security Rules
- **IAP-only access** — all VMs: SSH via `--tunnel-through-iap` only
- **Internal VPC connectivity** — `default-allow-internal` firewall rule allows 10.128.0.0/9
- **No public exposure** — FastAPI on 127.0.0.1 (dev) or 0.0.0.0 (staging internal VPC only)
- **PostgreSQL internal only** — listens on 127.0.0.1:5432, reachable via internal IPs

---

## 4. DATABASES — POSTGRESQL

### Database Separation (ABSOLUTE RULE)
| Database | Purpose | Host | User | NEVER TOUCH FROM |
|----------|---------|------|------|------------------|
| `ftd_lakehouse` | **PRODUCTION** | `ftd-postgres-vm` internal `10.168.0.3` | `ftd_app` | CI/CD, development, any automation |
| `ftd_lakehouse_test` | Layer 3 test DB | Same | `ftd_app` | Only Layer 3 integration tests |
| `ftd_lakehouse_api_test` | Layer 4/5 API test DB (dev) | Same | `ftd_app` | Layer 4/5 integration tests, manual API testing |
| `ftd_lakehouse_staging` | **STAGING** (Layer 5) | Same | `ftd_app` | Only staging deploy pipeline |

### Connection Paths
```
Development (local/ftd-test):    IAP tunnel → ftd-postgres-vm:5432 (internal) → ftd_lakehouse_api_test
Staging (ftd-staging-api):       Internal VPC → ftd-postgres-vm:5432 (internal) → ftd_lakehouse_staging
```

### Environment Variables for PostgreSQL
**On `ftd-test` VM (in `start_app.sh`):**
```bash
PGHOST=10.168.0.3
PGPORT=5432
PGDATABASE=ftd_lakehouse_api_test
PGUSER=ftd_app
PGPASSWORD=<from GitHub Actions secret FTD_TEST_PG_PASSWORD>
```

**On `ftd-staging-api` VM (in `start_app.sh`):**
```bash
PGHOST=10.168.0.3
PGPORT=5432
PGDATABASE=ftd_lakehouse_staging
PGUSER=ftd_app
PGPASSWORD=<from GitHub Actions secret FTD_STAGING_PG_PASSWORD>
```

### Connection from VMs to PostgreSQL (Internal VPC)
```bash
# From ftd-test or ftd-staging-api VM:
psql -h 10.168.0.3 -U ftd_app -d ftd_lakehouse_api_test    # dev
psql -h 10.168.0.3 -U ftd_app -d ftd_lakehouse_staging     # staging
# Uses internal IP, no IAP needed
```

### Database Schema (Auth Tables)
```sql
-- Core auth tables (migrations 001-005)
users(id SERIAL PK, email TEXT UNIQUE NOT NULL, password_hash TEXT, 
      firebase_uid TEXT UNIQUE, created_at TIMESTAMP, updated_at TIMESTAMPTZ, is_active BOOLEAN DEFAULT TRUE)

permissions(id SERIAL PK, name TEXT UNIQUE NOT NULL, description TEXT)

user_permissions(user_id INTEGER FK, permission_id INTEGER FK, PK(user_id, permission_id))

user_permissions_index(user_id INTEGER, permission_name TEXT, 
                       indexes: user_id, permission_name, composite(user_id, permission_name))
```

### Critical Database Behavior (LEARNED THE HARD WAY)
1. **`query()` helper in `app/db.py` calls `fetchall()`** — ONLY works for SELECT. DML (DELETE, INSERT, UPDATE) must use `execute()` helper.
2. **`execute()` helper MUST call `conn.commit()`** — psycopg2 pool doesn't auto-commit. Without commit, DML silently rolls back when connection returns to pool.
3. **`ARRAY_AGG(permission_name)` returns `[None]` not `[]` when no rows** — Fix: `ARRAY_AGG(permission_name) FILTER (WHERE permission_name IS NOT NULL)` (Layer 2 defect, documented but not fixed).
4. **Connection pool**: `SimpleConnectionPool` in `app/db.py`, `get_connection()` context manager guarantees rollback on exception.

---

## 5. AUTHENTICATION & AUTHORIZATION

### Architecture
```
Firebase (external identity) → Firebase ID token → FastAPI AuthMiddleware → 
  validate_firebase_token_with_reason() → Firebase Admin SDK → verified (firebase_uid, email) →
  synchronize_user() → PostgreSQL User record (linked by firebase_uid) →
  get_current_application_user dependency → service layer
```

### Key Files
| File | Purpose |
|------|---------|
| `app/auth/firebase_auth.py` | Firebase Admin SDK init (`ApplicationDefault()`), `validate_firebase_token_with_reason()` |
| `app/auth/firebase_config.py` | Env vars: `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH`, `FIREBASE_AUTH_ENABLED` |
| `app/auth/middleware.py` | `AuthMiddleware` — validates Bearer token (Firebase first, then internal JWT), attaches to `request.state` |
| `app/auth/user_sync.py` | `synchronize_user(identity)` — creates/reuses PostgreSQL User from Firebase identity |
| `app/auth/dependencies.py` | `get_current_application_user`, `get_current_permissions`, `require_permission(perm)` |
| `app/auth/permissions.py` | 8 permission constants: `tickers.search`, `tickers.prices`, `tickers.news`, `tickers.filings`, `tickers.timeline`, `tickers.fiscal_year_end`, `filings.read`, `search.read` |

### Firebase Project
| Property | Value |
|----------|-------|
| **Project ID** | `ftd-2026` (note the hyphen!) |
| **Auth Provider** | Email/Password (enabled in Firebase Console) |
| **Admin SDK Key** | `/home/isabellabutera/firebase-key.json` on `ftd-test` VM (service account `firebase-adminsdk-fbsvc@ftd-2026.iam.gserviceaccount.com`) |
| **Web API Key** | `AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8` (SAFE in repo, client-side only) |
| **Test Account** | `test-firebase-ftd@ftd2026.test` / `TestPass123!` / UID: `UixIk5h0kFS6uRy9CdM3DvpiwDw1` |

### Internal JWT (Legacy, still supported)
| Property | Value |
|----------|-------|
| **Secret** | `JWT_SECRET_KEY` (env var) |
| **Algorithm** | HS256 |
| **Expiration** | 60 minutes (`JWT_EXPIRATION_MINUTES`) |
| **Issuer** | `ftd-auth` |
| **Audience** | `ftd-api` |
| **Token Version** | 1 (`JWT_TOKEN_VERSION`) — invalidates all tokens on increment |
| **BCrypt Rounds** | 12 |

---

## 6. SECRETS & CONFIGURATION (METADATA ONLY — NO VALUES)

| Secret/Config | Stored In | Consumed By | How to Access |
|---------------|-----------|-------------|---------------|
| `FTD_TEST_PG_PASSWORD` | GitHub Actions Secret | Deploy workflow → injected into `start_app.sh` via `--command` | `gh secret list` / GitHub UI |
| `FTD_STAGING_PG_PASSWORD` | GitHub Actions Secret | Staging deploy workflow → injected into `start_app.sh` via `--command` | `gh secret list` / GitHub UI |
| PostgreSQL Password | VM only: `/home/isabellabutera/start_app.sh` | FastAPI via `PGPASSWORD` env var | SSH to VM, cat file |
| Firebase Admin SDK Key | VM only: `/home/isabellabutera/firebase-key.json` | `FIREBASE_CREDENTIALS_PATH` | SSH to VM, cat file |
| Firebase Web API Key | **In repo** (`context/figma_prototype/src/app/App.tsx`) | React `firebaseConfig` | Public by design |
| Workload Identity Provider | GCP: `projects/767713105/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider` | GitHub Actions auth | Pre-configured |
| Service Account (GitHub Actions) | `github-actions-deploy@ftd2026.iam.gserviceaccount.com` | GCP deployments | IAM binding exists |
| GNews API Key | GCP Secret Manager: `gnews-api-key` | GNews Cloud Function | `--set-secrets=GNEWS_API_KEY_SECRET=gnews-api-key:latest` |
| Finnhub API Key | GCP Secret Manager: `finnhub-api-key` | Prices pipeline on `data-ingest-vm` | `secretmanager_v1` client in `prices/main.py` |

**RULE**: Never commit secrets. VM-only secrets live only on VMs. GitHub Actions uses Workload Identity (no key files).

---

## 7. DEPLOYMENT — GITHUB ACTIONS

### Branch-to-Environment Mapping (CRITICAL)
| Branch | Environment | Target VMs | Database |
|--------|-------------|------------|----------|
| `rawdataingestion` | Development | `ftd-test` (monolithic) | `ftd_lakehouse_api_test` |
| `staging` | Staging | `ftd-staging-web` + `ftd-staging-api` | `ftd_lakehouse_staging` |

**Rule**: Branch name alone determines target. No commit-message keywords for app deployment.

### Workflow: `.github/workflows/deploy.yml`
- **Trigger**: Push to `rawdataingestion` OR `staging` OR `workflow_dispatch`
- **Auth**: Workload Identity → `github-actions-deploy@ftd2026.iam.gserviceaccount.com`
- **CI Gate**: Waits for CI workflow to pass on same commit (max 3 min) — polling step in each job
- **Records**: Deployed revision (SHA, branch, commit message, timestamp, environment, workflow_run_id)

### Development Deployment (`rawdataingestion` branch)
Single job `deploy-development` → targets `ftd-test` VM (monolithic: FastAPI + React + nginx)

### Staging Deployment (`staging` branch) — 4 Jobs with Dependencies
```
deploy-staging-migrations (needs: CI gate)
    ↓
deploy-staging-backend (needs: migrations) → ftd-staging-api (FastAPI on 0.0.0.0:8000)
    ↓
deploy-staging-web (needs: backend) → ftd-staging-web (nginx on 8080, proxies /api/* → 10.168.0.7:8000)
    ↓
deploy-staging-verify (needs: backend + web) → 8 end-to-end checks
```

### CI Gate Enforcement
- Each staging job has `Verify CI passed` step that polls `gh run list --workflow="CI"` for same commit SHA
- Failed CI on PR to `staging` → **no deployment triggered** (verified)

### Manual Deploy Recipe (if CI fails)
```bash
# Trigger via workflow_dispatch (requires target_environment input)
gh workflow run "Deploy to GCP" -f target_environment=staging --ref staging
```

### Startup Script: `/home/isabellabutera/start_app.sh` (on VM, NOT in repo)
```bash
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/home/isabellabutera/app/app}"
VENV_DIR="${VENV_DIR:-/home/isabellabutera/app/.venv}"
LOG_FILE="${LOG_FILE:-/tmp/uvicorn.log}"
HOST="${HOST:-127.0.0.1}"  # Default localhost; override to 0.0.0.0 for multi-VM staging

export PGHOST="${PGHOST:-10.168.0.3}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-ftd_lakehouse_api_test}"
export PGUSER="${PGUSER:-ftd_app}"
export PGPASSWORD="${PGPASSWORD:-}"

# ... Firebase env vars ...

cd "${APP_DIR}"
nohup "${VENV_DIR}/bin/uvicorn" app.main:app --host "${HOST}" --port 8000 > "${LOG_FILE}" 2>&1 &
```

### Deployable Components (conditional on commit message)
| Component | Trigger Keywords | Target |
|-----------|------------------|--------|
| Start Price VM Cloud Function | `start-price-vm`, `deploy` | Cloud Functions |
| GNews Cloud Function | `gnews`, `deploy` | Cloud Functions |
| Prices VM Script | `prices`, `deploy` | `data-ingest-vm` |
| **Application (dev)** | `app`, `backend`, `frontend`, `deploy` | `ftd-test` |
| **Application (staging)** | N/A (branch-based) | `ftd-staging-web` + `ftd-staging-api` |

---

## 8. APPLICATION ARCHITECTURE (LAYERS)

### Layer 1: Firebase Authentication (COMPLETED)
- `app/auth/middleware.py` — `AuthMiddleware` validates Firebase ID token OR internal JWT
- `app/auth/firebase_auth.py` — Firebase Admin SDK verification
- `app/auth/user_sync.py` — `synchronize_user()` creates PostgreSQL User from Firebase identity
- **Public paths**: `/health`, `/auth/login`, `/auth/me`, `/docs*`, `/openapi.json`, `/redoc`, `OPTIONS` (CORS)

### Layer 2: Database Access Boundary (maintenance-prof Layer 2 — COMPLETED 2.1-2.4)
| File | Purpose |
|------|---------|
| `app/db.py` | `SimpleConnectionPool`, `get_connection()`, `query_dict()`, `query()`, `execute()` |
| `app/auth/repository.py` | 9 user queries + 2 relational: `get_user_with_permissions` (ARRAY_AGG), `get_user_with_permission_details` (multi-JOIN) |
| `app/services/user_service.py` | Validation, error mapping, orchestrates repository |
| `app/auth/router.py` | FastAPI endpoints: CRUD + permissions |

**Transaction Convention**:
- Reads: `query_dict()` / `query()` — pool manages
- Writes: `get_connection()` with `conn.autocommit=False` + explicit `conn.commit()`
- `execute()` for DML without RETURNING — calls `conn.commit()`

### Layer 3: Service Layer (COMPLETED)
| File | Purpose |
|------|---------|
| `app/services/user_service.py` | 7 operations: `get_authenticated_user`, `get_authenticated_user_by_id`, `get_user_permissions`, `get_user_with_permissions`, `create_user`, `update_user`, `delete_user`, `get_user_with_permission_details` |
| `app/services/exceptions.py` | `UserServiceError`, `UserNotFoundError`, `UserAlreadyExistsError`, `UserValidationError` |
| **Rule** | NO FastAPI/Starlette imports in service layer (verified by AST test) |

### Layer 4: FastAPI API Boundary (COMPLETED)
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, CORS, AuthMiddleware, exception handlers, router registration |
| `app/routes/users.py` | `/users/me`, `/users/me/permissions`, `/users/me/permission-details` |
| `app/auth/router.py` | `/auth/login`, `/auth/me/user`, `/auth/users/{id}`, `/auth/users`, `/auth/me/user` (PATCH/DELETE), `/auth/me/user/permissions` |

### Layer 5: React Frontend (COMPLETED)
| File | Purpose |
|------|---------|
| `context/figma_prototype/src/app/App.tsx` | Single-file React app (~2745 lines), Firebase login, API client, profile rendering |
| **API Base** | `http://127.0.0.1:18000` (IAP tunnel) |
| **Firebase Config** | `projectId: "ftd-2026"`, `apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8"` |
| **Flow** | Login → Firebase → Bearer token → `/auth/me/user` + `/users/me/permissions` → Profile |

---

## 9. TESTING

### Test Files
| File | Scope | DB Required |
|------|-------|-------------|
| `tests/test_hasher.py` | bcrypt hash/verify | No |
| `tests/test_token.py` | JWT create/verify | No |
| `tests/test_auth_middleware.py` | AuthMiddleware (mocked) | No |
| `tests/test_user_sync.py` | Firebase→PostgreSQL sync | Yes (skipped if no PG) |
| `tests/test_user_service.py` | Service layer (24 tests) | Yes (19 skipped if no PG) |
| `tests/test_db.py` | DB boundary (14 tests) | Yes (mocked + PG) |
| `tests/test_users_router.py` | Router endpoints (mocked + 14 PG) | Yes (PostgreSQL class) |

### Running Tests
```bash
# All tests (unit only, no PG):
python -m pytest tests/test_hasher.py tests/test_token.py tests/test_auth_middleware.py -v

# With PostgreSQL (requires IAP tunnel + env vars):
export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=ftd_lakehouse_api_test PGUSER=ftd_app PGPASSWORD=<password>
python -m pytest tests/test_user_service.py tests/test_users_router.py -v
```

### Test Database Setup (for PG tests)
```bash
# 1. Start IAP tunnel
gcloud compute start-iap-tunnel ftd-postgres-vm 5432 --zone=us-west2-a --project=ftd2026 --local-host-port=127.0.0.1:5432 &

# 2. Export env vars
export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=ftd_lakehouse_api_test PGUSER=ftd_app PGPASSWORD=<password>

# 3. Run tests
python -m pytest tests/test_user_service.py::TestUserService -v
```

---

## 10. INGESTION PIPELINES (BACKGROUND — NOT ACTIVE WORK)

### SEC 8-K Pipeline (`sec/`)
- **Trigger**: Cloud Scheduler 03:30 UTC → starts `data-ingest-vm` → startup script runs `sec/src/main.py`
- **Target**: Fortune 500 tickers → CIKs → 8-K filings → `gs://raw-data-strg/SEC/8-K/{CIK}/{accession}/`
- **Safety**: `ALLOW_LOCAL_EXECUTION=false` (refuses to run off-GCP), byte budgets, self-terminating VM

### GNews Pipeline (`gnews/`)
- **Type**: Cloud Function (Gen1, Python 311, 512MB, 300s)
- **Trigger**: HTTP (Cloud Scheduler)
- **Auth**: Secret Manager `gnews-api-key`
- **Output**: `gs://raw-data-strg/gnews/YYYY-MM-DD/batch_XXX.json`

### Finnhub Prices (`prices/`)
- **Type**: Script on `data-ingest-vm` via cron `0 22 * * *`
- **Auth**: Secret Manager `finnhub-api-key`
- **Rate**: 1 req/sec, backoff on 429, abort after 5 consecutive failures
- **Dedup**: Skips if day's blob exists
- **Output**: `gs://raw-data-strg/prices/YYYY-MM-DD/data.jsonl`

### Lakehouse Pipeline (`lakehouse/`)
- **Runs**: Locally (manual)
- **Input**: Raw data from `raw-data-strg`
- **Output**: Parquet to `processed-layer-one/lakehouse/staging/`
- **BigQuery**: External tables in `ftd2026.lakehouse`, views in `ftd2026.analytics`

---

## 11. FRONTEND — REACT PROTOTYPE

| Property | Value |
|----------|-------|
| **Location** | `context/figma_prototype/` |
| **Framework** | React 18 + Vite + Tailwind + shadcn/ui |
| **Dev Server** | `npm run dev` → `localhost:5173` |
| **Build** | `npm run build` → `dist/` |
| **API Base** | `http://127.0.0.1:18000` (IAP tunnel) |
| **Firebase Config** | `projectId: "ftd-2026"` (hyphen!), `apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8"` |
| **CORS** | FastAPI allows `localhost:5173` origin |
| **Auth Flow** | `signInWithEmailAndPassword` → `onAuthStateChanged` → `getIdToken()` → `Authorization: Bearer` |

---

## 12. SECURITY RULES (NON-NEGOTIABLE)

1. **FastAPI binds to `127.0.0.1:8000` ONLY** — never `0.0.0.0`
2. **PostgreSQL on private VPC ONLY** — internal IP `10.168.0.3`, no public firewall rules for 5432
3. **IAP-only access** — no public SSH, no public API, no public PostgreSQL
4. **No production DB writes from CI/CD** — uses `ftd_lakehouse_api_test` only
5. **No Docker/Kubernetes** — direct file sync + `nohup`
6. **No systemd** — `start_app.sh` manages process
7. **No credentials in repo** — VM-only, GitHub Secrets, Secret Manager
8. **Firebase Web API key is safe to commit** — client-side, public by design
9. **React bundle contains NO server secrets** — only Firebase client config

---

## 13. KNOWN RABBIT HOLES & SOLUTIONS (DON'T REDISCOVER)

| Problem | Solution | Location |
|---------|----------|----------|
| **SSH to ftd-test times out** | Use `--tunnel-through-iap` flag (firewall only allows IAP range) | `gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap` |
| **SSH to ftd-postgres-vm fails after restart** | SSH daemon banner exchange fails; resize VM (e2-micro→e2-medium) or use Serial Console to restart networking | `gcloud compute instances update ftd-postgres-vm --machine-type=e2-medium --zone=us-west2-a` |
| **IAP tunnel to PostgreSQL fails** | VM network interface `ens4` failed DHCP after restart; same fix as above | Check Serial Console: `ens4: Could not set DHCPv4 address` |
| **`query()` doesn't commit DML** | Use `execute()` helper (added in `app/db.py`) which calls `conn.commit()` | `app/db.py`, `app/auth/index_maintainer.py` |
| **`ARRAY_AGG` returns `[None]` not `[]`** | Add `FILTER (WHERE permission_name IS NOT NULL)` to query | `app/auth/repository.py:104-115` (Layer 2 defect) |
| **Token corrupted in shell** | Never pass JWT via command line; write Python test script that reads token programmatically | `/tmp/test_auth_http.py` pattern |
| **Startup directory matters** | `start_app.sh` must run from `/home/isabellabutera/app` for Python imports to work | Deploy workflow `cd /home/isabellabutera/app` |
| **Firebase project ID mismatch** | React had `"ftd2026"`, backend uses `"ftd-2026"` (with hyphen) | Fixed in `App.tsx` |
| **Monkeypatch target wrong after refactor** | Patch the name in the consuming module's namespace, not the defining module | `app.auth.dependencies.get_authenticated_user` not `app.services.user_service.get_authenticated_user` |
| **Sync runs before commit** | `sync_user_permissions_index()` uses separate connection; must run AFTER `conn.commit()` in test setup | `tests/test_users_router.py::_setup_test_data()` |
| **Empty Bearer token rejected by httpx** | `httpx` validates headers at protocol level; this is expected behavior | Don't test empty token at HTTP level |
| **VM service account lacks Secret Manager scope** | Use `ApplicationDefault()` credentials or local key file at `FIREBASE_CREDENTIALS_PATH` | `firebase_auth.py` handles both |
| **nginx 502 Bad Gateway on staging** | Backend VM hostname not in `/etc/hosts`; use internal IP directly in nginx `proxy_pass` | `proxy_pass http://10.168.0.7:8000/;` |
| **nginx 403 Forbidden on staging** | Root path wrong; React builds to `dist/dist/` not `dist/` | nginx root: `/home/isabellabutera/frontend/dist/dist` |
| **FastAPI on staging not reachable from Web VM** | FastAPI bound to `127.0.0.1`; must use `HOST=0.0.0.0` for internal VPC access | `start_app.sh` uses `HOST` env var, default `127.0.0.1` |
| **`version.json` shell variables not expanded** | Heredoc used `'EOF'` (literal) instead of `EOF` | Use unquoted `EOF` for `$()` expansion |
| **CI `needs: ci` invalid in deploy workflow** | Cannot reference job in another workflow; use polling step instead | Each deploy job has `Verify CI passed` step |
| **Python `python3-venv` missing on new VM** | Install `python3.11-venv` or `python3-venv` in provisioning script | Added to `provision_staging_vms.sh` |

---

## 14. GCP RESOURCES & PERMISSIONS

| Resource | Name/ID | Purpose |
|----------|---------|---------|
| **GCP Project** | `ftd2026` | All resources |
| **Workload Identity Pool** | `github-actions-pool` | GitHub Actions auth |
| **Workload Identity Provider** | `github-actions-provider` | Maps GitHub → GCP |
| **Deploy Service Account** | `github-actions-deploy@ftd2026.iam.gserviceaccount.com` | CI/CD deployments |
| **GNews Service Account** | `gnews-ingestion-sa@ftd2026.iam.gserviceaccount.com` | GNews Cloud Function |
| **VM Service Account (all VMs)** | `767713105-compute@developer.gserviceaccount.com` | Default compute SA |
| **Firebase Admin SDK SA** | `firebase-adminsdk-fbsvc@ftd-2026.iam.gserviceaccount.com` | Token verification |
| **Firewall: allow-iap-ssh** | Allows TCP 22 from `35.235.240.0/20` (IAP range) | SSH access |
| **Firewall: default-allow-internal** | Allows all protocols from `10.128.0.0/9` | Internal VPC connectivity |

### IAM Roles (Key Ones)
- `github-actions-deploy`: `roles/secretmanager.secretAccessor`, `roles/cloudfunctions.developer`, `roles/compute.instanceAdmin.v1`
- `gnews-ingestion-sa`: `roles/secretmanager.secretAccessor`, `roles/storage.objectCreator`
- VM default SA: `roles/secretmanager.secretAccessor` (but lacks OAuth scopes for Secret Manager API)

---

## 15. ENVIRONMENT VARIABLES REFERENCE

### On `ftd-test` VM (in `start_app.sh`)
```bash
PGHOST=10.168.0.3
PGPORT=5432
PGDATABASE=ftd_lakehouse_api_test
PGUSER=ftd_app
PGPASSWORD=<from GitHub secret>
FIREBASE_PROJECT_ID=ftd-2026
FIREBASE_CREDENTIALS_PATH=/home/isabellabutera/firebase-key.json
FIREBASE_AUTH_ENABLED=true
```

### On `ftd-staging-api` VM (in `start_app.sh`)
```bash
PGHOST=10.168.0.3
PGPORT=5432
PGDATABASE=ftd_lakehouse_staging
PGUSER=ftd_app
PGPASSWORD=<from GitHub secret FTD_STAGING_PG_PASSWORD>
FIREBASE_PROJECT_ID=ftd-2026
FIREBASE_CREDENTIALS_PATH=/home/isabellabutera/firebase-key.json
FIREBASE_AUTH_ENABLED=true
HOST=0.0.0.0
```

### For Local Test Runner (IAP tunnel)
```bash
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=ftd_lakehouse_api_test
PGUSER=ftd_app
PGPASSWORD=<same password>
```

### For PostgreSQL Admin (via IAP tunnel)
```bash
PGHOST=127.0.0.1
PGPORT=5432  # or 5433 if using alternate local port
PGDATABASE=ftd_lakehouse  # or ftd_lakehouse_test
PGUSER=ftd_app
PGPASSWORD=<password>
```

### React (in `App.tsx`)
```typescript
const API_BASE = "http://127.0.0.1:18000";
const firebaseConfig = {
  projectId: "ftd-2026",
  apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8",
  // ... other config
};
```

---

## 16. FILE LOCATIONS QUICK REFERENCE

| Category | Path |
|----------|------|
| **FastAPI App** | `app/` |
| **Main Entry** | `app/main.py` |
| **Database** | `app/db.py` |
| **Auth Middleware** | `app/auth/middleware.py` |
| **Auth Dependencies** | `app/auth/dependencies.py` |
| **Auth Router** | `app/auth/router.py` |
| **Auth Models** | `app/auth/models.py` |
| **Auth Repository** | `app/auth/repository.py` |
| **Firebase Auth** | `app/auth/firebase_auth.py` |
| **User Sync** | `app/auth/user_sync.py` |
| **Service Layer** | `app/services/user_service.py` |
| **Service Exceptions** | `app/services/exceptions.py` |
| **User Routes** | `app/routes/users.py` |
| **Migrations** | `app/auth/migrations/001-005_create_auth_tables.sql` |
| **Tests** | `tests/` |
| **React App** | `context/figma_prototype/src/app/App.tsx` |
| **Deploy Workflow** | `.github/workflows/deploy.yml` |
| **CI Workflow** | `.github/workflows/ci.yml` |
| **Startup Script** | `scripts/start_app.sh` (deployed to VM) |
| **VM Startup Script** | `/home/isabellabutera/start_app.sh` (on VM only) |
| **Firebase Key** | `/home/isabellabutera/firebase-key.json` (on VM only) |
| **Provisioning Script** | `scripts/provision_staging_vms.sh` (creates ftd-staging-web + ftd-staging-api) |
| **Migration Script** | `scripts/apply_staging_migrations.sh` (idempotent staging DB migrations) |
| **Immutable Prompts (Old)** | `context/layers-prompts/` |
| **Immutable Prompts (Current)** | `context/maintenance-prof/` |
| **Historical Memory** | `context/MEMORY.md` (4592 lines) |
| **Audit Report** | `context/maintenance-prof/layer-four-audit.md` |

---

## 17. COMMON COMMANDS CHEAT SHEET

### VM Access
```bash
# ftd-test (dev app server)
gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap

# ftd-staging-web (staging frontend)
gcloud compute ssh ftd-staging-web --zone=us-west2-a --project=ftd2026 --tunnel-through-iap

# ftd-staging-api (staging backend)
gcloud compute ssh ftd-staging-api --zone=us-west2-a --project=ftd2026 --tunnel-through-iap

# ftd-postgres-vm (database)
gcloud compute ssh ftd-postgres-vm --zone=us-west2-a --project=ftd2026 --tunnel-through-iap

# Run command on VM without interactive shell
gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap --command="YOUR_COMMAND"
```

### PostgreSQL Access
```bash
# IAP tunnel (run in background)
gcloud compute start-iap-tunnel ftd-postgres-vm 5432 --zone=us-west2-a --project=ftd2026 --local-host-port=127.0.0.1:5432 &

# Connect via tunnel
PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=ftd_lakehouse_api_test PGUSER=ftd_app PGPASSWORD='...' psql

# One-off command via SSH (works even when tunnel fails)
gcloud compute ssh ftd-postgres-vm --zone=us-west2-a --project=ftd2026 --command="PGPASSWORD='...' psql -h 127.0.0.1 -U ftd_app -d ftd_lakehouse_api_test -c 'YOUR_SQL'"
```

### Deploy
```bash
# Trigger deploy via commit message
git commit -m "app deploy" && git push origin rawdataingestion

# Manual workflow dispatch (staging)
gh workflow run "Deploy to GCP" -f target_environment=staging --ref staging

# Manual workflow dispatch (development)
gh workflow run "Deploy to GCP" -f target_environment=development --ref rawdataingestion
```

### React
```bash
cd context/figma_prototype
npm run dev        # Dev server on localhost:5173
npm run build      # Production build to dist/
```

### Tests
```bash
# Unit tests only (no DB)
python -m pytest tests/test_hasher.py tests/test_token.py tests/test_auth_middleware.py -v

# With DB (requires tunnel + env vars)
export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=ftd_lakehouse_api_test PGUSER=ftd_app PGPASSWORD='...'
python -m pytest tests/test_user_service.py tests/test_users_router.py -v
```

### Logs
```bash
# FastAPI logs on VM
gcloud compute ssh ftd-test --zone=us-west2-a --project=ftd2026 --tunnel-through-iap --command="tail -f /tmp/uvicorn.log"
gcloud compute ssh ftd-staging-api --zone=us-west2-a --project=ftd2026 --tunnel-through-iap --command="tail -f /tmp/uvicorn.log"

# Deployment logs
gh run view --log
```

---

## 18. CURRENT STATE (AS OF LAYER 5 COMPLETION)

| Layer | Status | Notes |
|-------|--------|-------|
| **Firebase/App Foundation** | ✅ COMPLETE | Full vertical slice working |
| **maintenance-prof Layer 1** | ✅ COMPLETE | Deployment pipeline formalized |
| **maintenance-prof Layer 2** | ✅ COMPLETE | Database boundary, CRUD, relational agg, transactions |
| **maintenance-prof Layer 3** | ✅ COMPLETE | Service layer architecture, User domain CRUD |
| **maintenance-prof Layer 4** | ✅ COMPLETE | FastAPI API endpoints, error handlers |
| **maintenance-prof Layer 5** | ✅ COMPLETE | Multi-VM staging (Web + Backend + DB), CI/CD pipeline |

### Active Blockers
- None — infrastructure stable (ftd-postgres-vm resized to e2-medium)

### Known Defects (Documented, Not Fixed)
1. `get_user_with_permissions` returns `[None]` for users with no permissions (needs `FILTER WHERE permission_name IS NOT NULL`)
2. `ftd-postgres-vm` SSH/PostgreSQL fails after stop/start (network interface DHCP failure) — resize VM to fix

---

## 19. GIT HISTORY (KEY COMMITS)

| Commit | Initiative | Description |
|--------|------------|-------------|
| `30dbf884` | Auth Phases 1-3 | 11 files: migrations, auth infrastructure, login endpoint |
| `ad0c4cbd` | Auth Phase 4 | 3 files: middleware, dependencies, permissions |
| `adc10dee` | Auth Phase 5 | 3 files: seed_data, index_maintainer, composite index |
| `20af2fd5` | Auth Phase 6 | 4 route files: require_permission on all 9 endpoints |
| `5cc0c38f` | Layer 1.1 | 6 files: Firebase Auth integration |
| `bab59f6c` | Layer 2.1 | Service layer foundation |
| `c1f003b4` | Layer 2.2 | User CRUD contract |
| `831c6ddc` | Layer 2.3 | Relational aggregation |
| `cf734275` | Layer 2.4 | Query/transaction integrity (execute() fix) |
| `2395704c` | Layer 3.1 | Service layer architecture |
| `765198db` | Layer 3.2 | User domain CRUD |
| `f7590b53` | Layer 3.3 | Controlled aggregation |
| `a8ada3d5` | Layer 3.4 | Service validation |

---

## 20. WHAT AN AGENT MUST KNOW BEFORE TOUCHING ANYTHING

1. **Check which initiative you're in** — `maintenance-prof` (current) vs `layers-prompts` (historical)
2. **Never modify immutable prompts** — `context/layers-prompts/` and `context/maintenance-prof/` are read-only specs
3. **Never push to `main`** — all work on `rawdataingestion` (dev) or `staging` (staging)
4. **Never expose ports publicly** — IAP only, `127.0.0.1` (dev) or `0.0.0.0` internal VPC only (staging backend)
5. **Never touch `ftd_lakehouse`** — production database, read-only from automation
6. **Use correct database** — `ftd_lakehouse_api_test` (dev), `ftd_lakehouse_staging` (staging)
7. **Use IAP tunnels** — `--tunnel-through-iap` for SSH, `start-iap-tunnel` for PostgreSQL
8. **Secrets stay on VMs / GitHub Secrets / Secret Manager** — never in repo
9. **Service layer has no HTTP imports** — this is enforced by test
10. **Transaction convention** — `execute()` for DML with commit, `query_dict()` for SELECT
11. **Firebase project ID is `ftd-2026`** (with hyphen) — not `ftd2026`
12. **VM network issues after restart are infrastructure, not code** — resize VM or use Serial Console
13. **Branch determines environment** — `rawdataingestion` → dev (`ftd-test`), `staging` → staging (`ftd-staging-web` + `ftd-staging-api`)
14. **Staging is multi-VM** — Web VM (`ftd-staging-web:8080` nginx) proxies `/api/*` → Backend VM (`ftd-staging-api:8000` FastAPI) → Database VM (`ftd-postgres-vm:5432`)
15. **CI gate enforced on staging** — failed CI on PR to `staging` blocks deployment entirely

---

This is everything. Save it. Next time an agent starts, hand them this instead of letting them rediscover any of it.