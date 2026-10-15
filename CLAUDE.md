# CLAUDE.md — FTD Lakehouse Project Reference

**Project**: FTD (Financial Technology Data) Lakehouse — SEC filing research platform
**Current Commit**: `cc1de008` on `feature/frontend-modular-refactor`
**Environment**: Staging (deployed on GCP)
**Last Updated**: 2026-10-15

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Architecture Overview](#2-architecture-overview)
3. [GCP Infrastructure](#3-gcp-infrastructure)
4. [Authentication Flow](#4-authentication-flow)
5. [API Endpoints](#5-api-endpoints)
6. [Data Flow](#6-data-flow)
7. [Environment Variables](#7-environment-variables)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Backend Architecture](#9-backend-architecture)
10. [Deployment](#10-deployment)
11. [Testing](#11-testing)
12. [Layer Status](#12-layer-status)
13. [Known Issues](#13-known-issues)
14. [Developer Quick Reference](#14-developer-quick-reference)

---

## 1. Project Structure

```
gcloud-bucket-data/
├── app/                          # Backend: FastAPI application
│   ├── main.py                   # FastAPI entry point, middleware registration
│   ├── db.py                     # PostgreSQL connection pool, query utilities
│   ├── crud.py                   # Read-only data access functions (PostgreSQL)
│   ├── models.py                 # Pydantic response models
│   ├── auth/
│   │   ├── middleware.py         # AuthMiddleware — PUBLIC_PATHS, JWT/Firebase auth
│   │   ├── dependencies.py       # get_current_user, get_current_application_user, require_permission
│   │   ├── firebase_auth.py      # Firebase token validation
│   │   ├── token.py              # Internal JWT generation/verification
│   │   ├── user_sync.py          # Firebase-to-PostgreSQL user synchronization
│   │   ├── permissions.py        # Permission constants
│   │   ├── models.py             # User model, normalize_email
│   │   └── router.py             # Auth routes (/auth/login, /auth/register, /auth/me)
│   ├── services/
│   │   ├── vectorized_gcs.py     # GCS read operations for SEC data (692 lines)
│   │   ├── audit.py              # Audit logging to PostgreSQL + file logs
│   │   ├── db_access_counter.py  # Counters for PostgreSQL misuse detection
│   │   ├── data_service.py       # Application service layer
│   │   ├── user_fingerprint.py   # User identification from request
│   │   ├── user_service.py       # User lookup functions
│   │   └── exceptions.py         # Service-layer exceptions
│   ├── routes/
│   │   ├── tickers.py            # Ticker endpoints (/tracked, /search, /{ticker}/...)
│   │   ├── alerts.py             # Alert endpoints (/alerts)
│   │   ├── dashboard.py          # Dashboard stats (/dashboard/stats)
│   │   ├── filings.py            # Filing elements (/filings/{accession}/elements)
│   │   ├── search.py             # Content search (/search)
│   │   ├── workspaces.py         # Workspace CRUD (/workspaces)
│   │   ├── users.py              # User endpoints (/users)
│   │   └── admin.py              # Admin endpoints
│   ├── middleware/
│   │   └── audit_middleware.py   # Audit logging middleware
│   ├── migrations/               # Database migrations 001-009
│   ├── logging_config.py         # Structured logging setup
│   └── requirements.txt          # Python dependencies
├── context/
│   └── figma_prototype/          # Frontend: React + Vite + TypeScript
│       ├── src/
│       │   ├── app/
│       │   │   ├── App.tsx       # Root app component, routing, auth state
│       │   │   ├── firebase.ts   # Firebase auth initialization
│       │   │   ├── types.ts      # Page types, route definitions
│       │   │   └── components/   # shadcn-style UI components
│       │   ├── components/
│       │   │   ├── pages/        # Page components (DashboardPage, AlertsPage, etc.)
│       │   │   └── ui/           # Shared UI components (Badge, Card, Btn, etc.)
│       │   ├── hooks/
│       │   │   ├── index.ts      # useAlerts, useWorkspaces, useAuth, useDashboardStats
│       │   │   └── tickerHooks.ts # useTickerSearch, useTickerDashboard, useTickerNews, useTrackedTickers
│       │   ├── api/
│       │   │   └── index.ts      # API client: fetchWithAuth, getAlerts, getTrackedTickers, etc.
│       │   └── types/
│       │       └── index.ts      # TypeScript interfaces (TrackedTicker, DashboardStats, etc.)
│       ├── package.json          # Vite 6.3.5, React 18.3.1, 30+ shadcn dependencies
│       ├── vite.config.ts        # Vite config with figma asset resolver
│       └── dist/                 # Build output (deployed to web VM)
├── tests/                        # Backend tests (48 tests)
│   ├── test_api_endpoints.py     # API endpoint tests (auth, routes, response shapes)
│   └── test_user_sync.py         # User sync integration tests
├── scripts/
│   ├── start_app.sh              # Start/restart uvicorn on backend VM
│   ├── verify_deployment.sh      # Post-deployment verification script
│   └── provision_staging_vms.sh  # VM provisioning script
├── migrations/                   # Database migrations
└── CLAUDE.md                     # This file
```

### Git Repositories (split from original monorepo)

| Repo | GitHub | Branch | Status |
|---|---|---|---|
| FTD-BFE (backend) | `Aquawile/FTD-BE` | `feature/frontend-modular-refactor` | ✅ Pushed cc1de008 |
| FTD-FE (frontend) | `Aquawile/FTD-FE` | `main` | ✅ 1 commit (initial prototype) |
| ftd-cloud (infra) | `Aquawile/ftd-cloud` | `main` | ✅ Created |

---

## 2. Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │          Client (Browser)        │
                    │  React SPA + Firebase Auth       │
                    │  (https://...trycloudflare.com)  │
                    └──────┬───────────────┬───────────┘
                           │               │
                  (HTML/JS/CSS)    (API calls /api/*)
                           │               │
                    ┌──────▼───────┐   ┌───▼──────────┐
                    │ ftd-staging- │   │ ftd-staging- │
                    │    web VM    │   │   api VM     │
                    │ (nginx:8080) │   │(uvicorn:8080)│
                    │              │   │              │
                    │ Proxy /api/  │◄──│  FastAPI     │
                    │ → API VM     │   │  AuthMiddleware│
                    └──────┬───────┘   └───┬──────────┘
                           │                │
                    ┌──────▼───────┐   ┌────▼──────────┐
                    │   Cloudflared│   │ PostgreSQL    │
                    │   Tunnel     │   │ ftd-postgres- │
                    │              │   │    vm (5432)  │
                    │ Local tunnel │   │               │
                    └──────────────┘   │ stg_gnews,    │
                                       │ tickers,      │
                    ┌────────────────┐ │ alerts, etc.  │
                    │ Google Cloud   │ │               │
                    │ Storage        │ └───────────────┘
                    │ ftd-vectorized-│       ▲
                    │ data           │       │
                    │ raw-data-strg  │  (DB access
                    └────────────────┘   for ticker
                                         metadata)
```

### Key Design Decisions

1. **SEC data in GCS, not PostgreSQL**: After Layer 8, SEC filing content (754K+ articles) is stored as vectorized JSON in GCS buckets. PostgreSQL only holds relational metadata (tickers, prices, news, user workspace data).

2. **Dual auth**: Firebase ID tokens OR internal JWT. The AuthMiddleware tries Firebase first, falls back to internal JWT verification.

3. **Public endpoints**: Certain endpoints bypass auth entirely (health, version, dashboard stats, tracked tickers, SEC file proxy) for unauthenticated access.

4. **DB access counters**: A thread-local counter system tracks any access to SEC data via PostgreSQL after migration. If counters > 0, the migration is incomplete.

---

## 3. GCP Infrastructure

### Project & Region
- **GCP Project**: `ftd2026`
- **Zone**: `us-west2-a`
- **OS User**: `isabellabutera`

### Virtual Machines

| VM Name | Internal IP | Port | Role | Key Paths |
|---|---|---|---|---|
| `ftd-postgres-vm` | `10.168.0.3` | 5432 | PostgreSQL 14 | DB: `ftd_lakehouse_staging` |
| `ftd-staging-api` | `10.168.0.7` | 8080 | Backend API | `/home/isabellabutera/app/`, `/home/isabellabutera/version.json` |
| `ftd-staging-web` | `10.168.0.6` | 8080 | Frontend (nginx) | `/home/isabellabutera/frontend/dist/`, `/home/isabellabutera/version.json` |

### Database
- **PostgreSQL**: `ftd_lakehouse_staging` on `ftd-postgres-vm:5432`
- **Users**: `ftd_app` (application), `postgres` (admin)
- **Password**: `5Ou+BkyuQT3izP72219jMLy2AobRdI3f`
- **Connection**: Local socket on `ftd-staging-api` (NOT remote connection to postgres VM)

### GCS Buckets
| Bucket | Purpose | Data |
|---|---|---|
| `ftd-vectorized-data` | Vectorized SEC filings | JSON files with `chunks` arrays, `sec_metadata` |
| `raw-data-strg` | Raw SEC filing HTML | `.htm` files organized by `SEC/{form}/{CIK}/{accession}/` |

### Cloudflare Tunnel (current)
- **URL**: `https://bunch-length-classic-caring.trycloudflare.com`
- **Proxy target**: `ftd-staging-web` localhost:8080 (nginx serves both frontend + proxies `/api/` to API VM)
- **Access**: Public, no IAP required for the tunnel itself

### Service Account
- `github-actions-deploy@ftd2026.iam.gserviceaccount.com` (used in CI/CD workflows)

---

## 4. Authentication Flow

### Two Auth Methods (tested in order by AuthMiddleware)

#### Method 1: Firebase Auth (primary)
1. User authenticates with Firebase (email/password)
2. Frontend gets Firebase ID token via `firebaseUser.getIdToken()`
3. `apiRequest()` sends `Authorization: Bearer <firebase_token>` header
4. AuthMiddleware calls `validate_firebase_token_with_reason(token)`
5. If valid: token contains `firebase_uid` and `email`
6. `get_current_application_user` looks up or creates user in PostgreSQL `users` table
7. Sets `request.state.firebase_uid`, `request.state.email`, `request.state.auth_method = "firebase"`

#### Method 2: Internal JWT (fallback)
1. User logs in via `/auth/login`
2. Backend generates JWT with `JWT_SECRET_KEY`
3. JWT contains `{"sub": user_id, "email": email}`
4. `fetchWithAuth()` reads token from `localStorage["auth_token"]`
5. AuthMiddleware tries Firebase first, fails, then calls `verify_token(token)`
6. Sets `request.state.user_id`, `request.state.email`, `request.state.auth_method = "internal"`

### Auth Components

| File | Responsibility |
|---|---|
| `app/auth/middleware.py` | `AuthMiddleware` — intercepts every request, checks PUBLIC_PATHS, validates tokens |
| `app/auth/firebase_auth.py` | `validate_firebase_token_with_reason()` — verifies Firebase ID token |
| `app/auth/token.py` | `verify_token()`, `create_token()` — internal JWT functions |
| `app/auth/dependencies.py` | `get_current_application_user()` — resolves user from request state |
| `app/auth/user_sync.py` | `synchronize_user()` — creates/updates user in PostgreSQL from Firebase identity |

### PUBLIC_PATHS (no auth required)

```python
PUBLIC_PATHS = {
    "/health",
    "/version",
    "/auth/login",
    "/auth/register",
    "/auth/me",
    "/dashboard/stats",
    "/tickers/tracked",
}
# Plus SEC proxy pattern: /tickers/*/content (SEC_PROXY_PREFIX/SUFFIX)
```

---

## 5. API Endpoints

### Public Endpoints (no auth)

| Method | Path | Description | Response Model |
|---|---|---|---|
| GET | `/health` | Health check + DB access counters | `{"status":"ok","db_access_counters":{},"db_access_detected":false}` |
| GET | `/version` | Deployment version metadata | `VersionMetadata` |
| GET | `/dashboard/stats` | Dashboard stats (articles, tickers, alerts, vectorized count) | `DashboardStats` |
| GET | `/tickers/tracked` | Tracked tickers list | `list[TrackedTicker]` |
| GET | `/tickers/{ticker}/filings/{accession}/content` | SEC filing content proxy | HTMLResponse |

### Auth-Required Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| POST | `/auth/login` | — | Internal JWT login |
| POST | `/auth/register` | — | Internal JWT registration |
| GET | `/auth/me` | — | Current user info |
| GET | `/alerts` | `tickers.*` implied | User-specific alerts |
| GET | `/tickers/search?q=...` | `tickers.search` | Ticker search |
| GET | `/tickers/{ticker}/prices` | `tickers.prices` | Historical prices |
| GET | `/tickers/{ticker}/news` | `tickers.news` | News articles |
| GET | `/tickers/{ticker}/timeline` | `tickers.timeline` | Timeline events |
| GET | `/tickers/{ticker}/filings` | `tickers.filings` | SEC filings list |
| GET | `/tickers/{ticker}/fiscal-year-end` | `tickers.fiscal_year_end` | Fiscal year end |
| GET | `/search?q=...` | `search.read` | Content search |
| GET | `/filings/{accession}/elements` | `filings.read` | Filing elements |
| GET | `/workspaces` | — | User workspaces |
| POST | `/workspaces` | — | Create workspace |
| GET | `/workspaces/{id}` | — | Workspace details |
| DELETE | `/workspaces/{id}` | — | Delete workspace |
| POST | `/workspaces/{id}/tickers` | — | Add ticker to workspace |
| DELETE | `/workspaces/{id}/tickers/{symbol}` | — | Remove ticker from workspace |
| GET | `/users/me` | — | User profile |
| GET | `/users/me/permissions` | — | User permissions |

### Key Data Models

```python
class TrackedTicker(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    evidence_score: Optional[float] = None
    hype_score: Optional[float] = None
    change_percent: Optional[float] = None
    price_as_of: Optional[str] = None

class DashboardStats(BaseModel):
    articles_count: int = 0        # From staging_sec_archive table
    tickers_count: int = 0         # COUNT DISTINCT from tickers table
    alerts_count: int = 0          # COUNT from alerts table
    evidence_score: Optional[float] = None
    vectorized_sec_count: int = 0  # count_vectorized_content() — GCS chunks

class AlertResponse(BaseModel):
    id: int
    ticker: Optional[str] = None
    type: str
    message: str
    read: bool = False
    severity: str = "medium"
    time: Optional[str] = None
```

---

## 6. Data Flow

### SEC Filing Data Flow (Post-Layer 8)

```
1. SEC EDGAR         (source data)
   → Python ETL      (parses filing HTML)
   → GCS: ftd-vectorized-data
      (sec-8k/{CIK}/{accession}/{ticker}-{date}.json)
   → PostgreSQL: tickers table (CIK resolution only)

Frontend Request:
  GET /api/tickers/NVDA/filings
  → tickers.py: route_get_filings()
  → vectorized_gcs.py: list_filings_for_ticker("NVDA")
  → _resolve_ticker_to_cik("NVDA")  [PostgreSQL tickers table]
  → _list_vectorized_blobs("sec-8k/{CIK}/")  [GCS]
  → Returns list of FilingSummary objects
```

### Dashboard Stats Flow

```
GET /api/dashboard/stats
  → dashboard.py: route_dashboard_stats()
  → count_vectorized_content()
      → Lists ALL .json blobs in ftd-vectorized-data (sec-8k/ + sec-10k/)
      → Downloads each, counts len(parsed["chunks"])
      → ThreadPoolExecutor(max_workers=20) for concurrent downloads
      → Returns total chunk count (currently 26,918)
  → query_dict("SELECT COUNT(*) FROM staging_sec_archive")  → articles_count (754,219)
  → query_dict("SELECT COUNT(DISTINCT symbol) FROM tickers")  → tickers_count (494)
  → query_dict("SELECT COUNT(*) FROM alerts")  → alerts_count (0)
```

### Ticker Tracked Data Flow

```
GET /api/tickers/tracked
  → tickers.py: route_get_tracked_tickers()
  → crud.py: get_tracked_tickers()
  → Reads from PostgreSQL: tickers table
  → join with latest_price_data (evidence_score, hype_score, change_percent)
  → Returns TrackedTicker objects (494 total)
```

### Alert Data Flow (requires auth)

```
GET /api/alerts
  → auth middleware: validates token (Firebase or JWT)
  → alerts.py: route_get_alerts()
  → dependencies: get_current_application_user()
  → crud.py: get_user_alerts(user_id, limit)
  → WHERE user_id = %s  (user-specific)
```

---

## 7. Environment Variables

### Backend (on `ftd-staging-api` VM)

Set in `/etc/systemd/system/ftd-api.service` and via `scripts/start_app.sh`:

| Variable | Value | Description |
|---|---|---|
| `PGHOST` | `10.168.0.3` | PostgreSQL VM internal IP |
| `PGPORT` | `5432` | PostgreSQL port |
| `PGDATABASE` | `ftd_lakehouse_staging` | Database name |
| `PGUSER` | `ftd_app` | Database user |
| `PGPASSWORD` | `5Ou+BkyuQT3izP72219jMLy2AobRdI3f` | Database password |
| `FIREBASE_PROJECT_ID` | `ftd-2026` | Firebase project |
| `FIREBASE_AUTH_ENABLED` | `true` | Enable Firebase auth |
| `JWT_SECRET_KEY` | *(secret)* | Internal JWT signing key |
| `JWT_EXPIRATION_MINUTES` | `10080` | 7 days (10080 minutes) |
| `PYTHONPATH` | `/home/isabellabutera/app` | Python module path |
| `VECTORIZED_OUTPUT_BUCKET` | `ftd-vectorized-data` | GCS bucket for SEC data |

### Service File

Location: `/etc/systemd/system/ftd-api.service`

```ini
[Unit]
Description=FTD API Server
After=network.target

[Service]
Type=simple
User=isabellabutera
WorkingDirectory=/home/isabellabutera/app
Environment=PGHOST=10.168.0.3
Environment=PGPORT=5432
Environment=PGDATABASE=ftd_lakehouse_staging
Environment=PGUSER=ftd_app
Environment=PGPASSWORD=5Ou+BkyuQT3izP72219jMLy2AobRdI3f
Environment=FIREBASE_PROJECT_ID=ftd-2026
Environment=FIREBASE_AUTH_ENABLED=true
Environment=JWT_SECRET_KEY=claude-s-secret-key-2025
Environment=JWT_EXPIRATION_MINUTES=10080
Environment=PYTHONPATH=/home/isabellabutera/app
ExecStart=/home/isabellabutera/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080

[Install]
WantedBy=multi-user.target
```

### Frontend (no env vars required)
- Firebase config is embedded in `src/app/firebase.ts`
- API_BASE = `/api` (relative, proxied by nginx)

---

## 8. Frontend Architecture

### Tech Stack
- **Framework**: React 18.3.1 + Vite 6.3.5
- **UI**: Radix UI components + shadcn-style patterns
- **Auth**: Firebase Auth (email/password)
- **Icons**: Lucide React
- **Styling**: Tailwind CSS 4.x
- **Charts**: Recharts 2.15.2
- **Date utils**: date-fns 3.6.0

### Key Components

| Component | Purpose | Real Data? |
|---|---|---|
| `DashboardPage.tsx` | Dashboard with stats, top movers, recent alerts | Yes (getTrackedTickers, getAlerts) |
| `AlertsPage.tsx` | Alerts list with filtering | Yes (useAlerts hook → /api/alerts) |
| `TickerDashboard.tsx` | Single ticker detail page | Yes (getTrackedTickers, apiRequest for prices/news/filings) |
| `SearchPage.tsx` | Ticker search + autocomplete | Yes (useTickerSearch hook → /api/tickers/search) |
| `LegacyLandingPage.tsx` | Landing page for unauthenticated users | Placeholder |
| `WorkspaceDetailPage.tsx` | Workspace detail view | Yes (workspace hooks) |

### Frontend API Client (`src/api/index.ts`)

```typescript
// Auth-aware fetch (for Firebase-authenticated endpoints)
export async function apiRequest(path, firebaseUser, options?): Promise<Response>
  → Gets Firebase ID token, adds Authorization: Bearer header

// LocalStorage token fetch (for internal JWT-authenticated endpoints)
async function fetchWithAuth<T>(endpoint, options?): Promise<T>
  → Reads localStorage["auth_token"], adds Bearer header if present
```

### Frontend Hooks (`src/hooks/index.ts`, `src/hooks/tickerHooks.ts`)

| Hook | Purpose | Endpoint |
|---|---|---|
| `useAlerts(limit, firebaseUser)` | Fetch user alerts | `GET /api/alerts?limit=N` |
| `useTrackedTickers(limit)` | Fetch all tracked tickers | `GET /api/tickers/tracked?limit=N` |
| `useTickerSearch(query, options)` | Search tickers | `GET /api/tickers/search?q=...&limit=...&sector=...&sort_by=...` |
| `useTickerDashboard(ticker)` | Fetch news/timeline/filings/tracked | Multiple endpoints |
| `useTickerNews(ticker)` | Fetch news for ticker | `GET /api/tickers/{ticker}/news` |
| `useTickerTimeline(ticker)` | Fetch timeline for ticker | `GET /api/tickers/{ticker}/timeline` |
| `useTickerFilings(ticker)` | Fetch filings for ticker | `GET /api/tickers/{ticker}/filings` |
| `useDashboardStats()` | Fetch dashboard stats | `GET /api/dashboard/stats` |
| `useAuth()` | Firebase auth state management | `/auth/me`, `/auth/login`, `/auth/register` |
| `useWorkspaces()` | Fetch user workspaces | `GET /api/workspaces` |

### Routing (in `App.tsx`)

```typescript
// Page navigation uses string-based routing within the SPA
const pages: Page[] = [
  "login", "register", "verify-email", "forgot-password", "onboarding-done",
  "dashboard", "search", "ticker", "ticker-timeline", "ticker-filings",
  "ticker-community", "ticker-comparison", "workspaces", "workspace-detail",
  "workspace-settings", "chat", "alerts", "profile", "admin",
  "admin-mapping", "admin-users", "admin-system"
];
```

### Important Field Name Mapping (Frontend ↔ Backend)

The frontend `TrackedTicker` type uses different field names from the backend:

| Backend (`models.py`) | Frontend (`types/index.ts`) |
|---|---|
| `symbol` | `symbol` |
| `name` | `name` |
| `sector` | `sector` |
| `current_price` | `current_price` |
| `evidence_score` | `evidence_score` |
| `hype_score` | `hype_score` |
| `change_percent` | `change_percent` |
| `price_as_of` | `price_as_of` |

**⚠️ CRITICAL**: The old mock data in `App.tsx` used `price`, `change`, `hype`, and `evidence` (shorter names). The real API returns the full field names above. If any component uses the old short names with real API data, it will crash with `TypeError: Cannot read properties of undefined`.

---

## 9. Backend Architecture

### Request Flow

```
HTTP Request
  → AuthMiddleware (app/auth/middleware.py)
    → Check PUBLIC_PATHS
    → If public: pass through
    → If protected: validate Firebase token → fallback to JWT
    → Set request.state (firebase_uid/user_id, email, auth_method)
  → AuditLogMiddleware (app/middleware/audit_middleware.py)
    → Records request timing, status
    → Calls log_api_request() for authenticated requests
  → Route handler (app/routes/*.py)
    → Calls require_permission() if decorator present
    → Calls service layer (app/services/)
    → Returns Pydantic model response
```

### Database Layer

| Component | File | Purpose |
|---|---|---|
| Connection pool | `app/db.py` | psycopg2 SimpleConnectionPool (minconn=1, maxconn=5) |
| Query functions | `app/crud.py` | Read-only SELECT queries, returns Pydantic models |
| User sync | `app/auth/user_sync.py` | Creates PostgreSQL user from Firebase identity |
| DB access counters | `app/services/db_access_counter.py` | Detects SEC data read from PostgreSQL (should be 0) |

### Service Layer

| Service | File | Purpose |
|---|---|---|
| Vectorized GCS | `app/services/vectorized_gcs.py` | All SEC data reads from GCS (592 lines) |
| Audit logging | `app/services/audit.py` | Logs API requests + SEC proxy access |
| Data service | `app/services/data_service.py` | Orchestrates data operations |
| User fingerprint | `app/services/user_fingerprint.py` | Extracts user identity from request |
| User service | `app/services/user_service.py` | User lookup operations |

### Key Service Functions (vectorized_gcs.py)

```python
# Resolve ticker symbol to SEC CIK
_resolve_ticker_to_cik(ticker: str) -> str | None
  → Tries PostgreSQL tickers table → unified_staging → GCS blob names

# List filings for a ticker
list_filings_for_ticker(ticker: str) -> list[FilingSummary]
  → Resolve CIK → list GCS blobs → parse sec_metadata → sort by date DESC

# Get filing elements/chunks
get_filing_elements_by_accession(accession_number: str) -> list[FilingElement]
  → Extract CIK from accession → fast-path directory lookup in GCS

# Count total vectorized content elements
count_vectorized_content() -> int
  → Lists all blobs in sec-8k/ and sec-10k/
  → Concurrent download (ThreadPoolExecutor, 20 workers)
  → Sums len(parsed["chunks"]) across all files

# Serve SEC filing content
get_filing_content_from_gcs(ticker, accession, cik) -> tuple[bytes, str, bool]
  → Looks in raw-data-strg bucket for .htm files
  → Falls back to SEC.gov if not found

# Get timeline events
get_timeline_from_gcs(ticker, start, end, limit, offset) -> list[TimelineEvent]
  → Resolve CIK → list GCS blobs → parse → filter by date range
```

### Middleware Order (important!)

1. **CORS** (`CORSMiddleware`) — first, handles OPTIONS
2. **Auth** (`AuthMiddleware`) — validates tokens, sets request.state
3. **Audit** (`AuditLogMiddleware`) — wraps request/response for logging

---

## 10. Deployment

### Backend Deployment

```bash
# 1. Build/prepare code locally
# 2. Copy code to API VM
gcloud compute scp --recurse app/* isabellabutera@ftd-staging-api:/home/isabellabutera/app/ \
  --zone us-west2-a --tunnel-through-iap

# 3. Copy version.json
gcloud compute scp version.json isabellabutera@ftd-staging-api:/home/isabellabutera/app/

# 4. Restart service
gcloud compute ssh isabellabutera@ftd-staging-api --zone us-west2-a --tunnel-through-iap \
  --command "sudo systemctl restart ftd-api.service"

# 5. Verify
gcloud compute ssh isabellabutera@ftd-staging-api --zone us-west2-a --tunnel-through-iap \
  --command "systemctl status ftd-api.service --no-pager -l"
```

### Frontend Deployment

```bash
# 1. Build locally
cd context/figma_prototype
npx vite build

# 2. Copy dist to web VM
gcloud compute scp --recurse dist/* isabellabutera@ftd-staging-web:/home/isabellabutera/frontend/dist/ \
  --zone us-west2-a --tunnel-through-iap

# 3. nginx is already configured to serve from dist/ — no restart needed for static files
# To reload nginx (if config changed):
gcloud compute ssh isabellabutera@ftd-staging-web --zone us-west2-a --tunnel-through-iap \
  --command "sudo nginx -s reload"
```

### Cloudflare Tunnel (for testing)

```bash
# Start a tunnel from web VM (which has nginx proxying /api/ to API VM)
gcloud compute ssh isabellabutera@ftd-staging-web --zone us-west2-a \
  --tunnel-through-iap \
  --command "nohup cloudflared tunnel --url http://localhost:8080 --no-autoupdate > /tmp/cf-tunnel.log 2>&1 &"

# Get the URL
gcloud compute ssh isabellabutera@ftd-staging-web --zone us-west2-a \
  --tunnel-through-iap --command "sleep 5 && grep 'trycloudflare' /tmp/cf-tunnel.log"
```

### Verification Script

```bash
bash scripts/verify_deployment.sh staging cc1de008
```

Checks:
1. Frontend served (HTML)
2. Web `/health` endpoint
3. API proxy `/api/health`
4. API version via proxy
5. Backend `/health`
6. Backend `/version`
7. Version metadata file on API VM
8. Version metadata file on Web VM
9. Cross-deployment check (other environment unchanged)
10. Database connectivity

---

## 11. Testing

### Backend Tests

```bash
# Run all tests
cd /app && python -m pytest tests/ -v

# Run only unit tests (no DB needed)
python -m pytest tests/ -m unit -v

# Run specific test file
python -m pytest tests/test_api_endpoints.py -v
```

**Test count**: 48 tests (all passing)

### Test Files

| File | Tests | Description |
|---|---|---|
| `tests/test_api_endpoints.py` | ~44 | API route tests — auth, permissions, response shapes |
| `tests/test_user_sync.py` | ~4 | User sync (Firebase → PostgreSQL) integration tests |

### Test Patterns

```python
# Auth mock fixture (autouse)
@pytest.fixture(autouse=True)
def _mock_firebase_auth():
    with patch(
        "app.auth.middleware.validate_firebase_token_with_reason",
        return_value=({"firebase_uid": "test-uid", "email": "test@example.com"}, None),
    ), patch("app.db.execute"):
        yield

# Permission override fixture
@pytest.fixture
def _mock_permissions():
    async def _fake_current_user():
        return {"user_id": 4, "email": "test@example.com"}
    async def _fake_permissions():
        return {"tickers.search", "tickers.prices", ...}
    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_current_permissions] = _fake_permissions
    yield
    app.dependency_overrides.pop(get_current_user, None)
```

---

## 12. Layer Status

### Completed Layers (1-12)

| Layer | Title | Status | Key Deliverables |
|---|---|---|---|
| L1 | Login-first entry, clean auth forms | ✅ Complete | LoginPage, RegisterPage, auth router |
| L2 | ProfilePage, sidebar, form fixes | ✅ Complete | ProfilePage, Admin nav, AccountPage |
| L3 | Dashboard stats API, live metrics | ✅ Complete | `/dashboard/stats`, frontend dashboard wiring |
| L4 | SEC proxy with GCS + SEC.gov fallback | ✅ Complete | `/tickers/{ticker}/filings/{accession}/content` |
| L5 | Refactor frontend, hooks, live data | ✅ Complete | Modular components, hooks, real API calls |
| L6 | Vectorized DB structure | ✅ Complete | GCS JSON format, chunk structure |
| L7 | GCS indexing, data pipeline | ✅ Complete | Blob listing, ticker CIK resolution |
| L8 | Migrate SEC data to GCS | ✅ Complete | All SEC endpoints read from GCS |
| L9 | Vectorize SEC data to GCS | ✅ Complete | `count_vectorized_content()`, migration 009 |
| L10 | Audit logging | ✅ Complete | `AuditLogMiddleware`, `api_usage_log` table |
| L11 | DB counter monitoring | ✅ Complete | `db_access_counter.py`, `/health` exposes counters |
| L12 | Production readiness | ✅ Complete | 14/14 gates passed (see `context/vectorized_db/layer-twelve.md`) |

### Migrations

| # | Name | Description |
|---|---|---|
| 001 | Initial schema | Core tables |
| 002 | Add user_permissions | Permission system |
| 003 | staging_gnews | News data table |
| 004 | api_usage_log | Audit log table |
| 005 | sec_vectorized_chunks | Vectorized data tracking |
| 006 | Add price columns | Price data fields |
| 007 | create_api_usage_log | Audit log structure |
| 008 | rename_sec_tables | Table reorganization |
| 009 | sec_vectorized_chunks_migration | Data migration tracking |

### PostgreSQL Tables (17 total)

| Table | Purpose | Rows |
|---|---|---|
| `tickers` | Ticker symbols, CIKs, sectors, scores | 494 |
| `latest_price_data` | Current prices, change % | ~494 |
| `staging_gnews` | News articles | ~754K |
| `staging_sec_archive` | SEC archive records | ~754K |
| `unified_staging` | Unified data staging | ~754K |
| `sec_vectorized_chunks` | Vectorized data tracking | 26,918 |
| `users` | Application users | 2 |
| `user_permissions` | User permission assignments | — |
| `permissions` | Permission definitions | 10+ |
| `workspaces` | User workspaces | — |
| `workspace_tickers` | Workspace-ticker mappings | — |
| `alerts` | User alerts | 0 |
| `api_usage_log` | Audit log | 109+ |
| `fiscal_year_end` | Fiscal year data | — |
| `price_history` | Historical prices | — |
| `sec_filings` | SEC filing metadata | — |
| `etf_holdings` | ETF holdings data | — |

---

## 13. Known Issues

### 1. TickerDashboard Field Name Mismatch (FIXED)

- **File**: `context/figma_prototype/src/components/pages/TickerDashboard.tsx`
- **Lines**: 150-166 (in the version before `cc1de008`)
- **Problem**: Code used `t.price`, `t.change`, `t.hype`, `t.evidence` — but the API returns `current_price`, `change_percent`, `hype_score`, `evidence_score`
- **Error**: `TypeError: Cannot read properties of undefined (reading 'toLocaleString')`
- **Fix**: Changed to use correct field names + `formatPrice()` helper

### 2. /tickers/search Requires Auth Despite Task Context Saying Public

- **File**: `app/auth/middleware.py`, `app/routes/tickers.py`
- **Status**: In current HEAD `cc1de008`, `/tickers/search` is NOT in `PUBLIC_PATHS` and has `require_permission("tickers.search")`
- **Frontend**: `searchTickers()` in `api/index.ts` uses `fetchWithAuth` (sends auth if available)
- **Note**: The task context mentioned making search public, but this was not implemented in the current commit. If unauthenticated search is needed, add `/tickers/search` to `PUBLIC_PATHS` and remove the `require_permission` decorator.

### 3. get_all_alerts() in CRUD (Unused)

- **File**: `app/crud.py` (line 449)
- **Status**: The function exists but is NOT imported or used by `alerts.py`. The alerts route uses `get_user_alerts()` (user-specific).
- **Note**: This was an attempt to make alerts public that was reverted in the route layer.

### 4. Articles Count Source

- The `/dashboard/stats` endpoint queries `staging_sec_archive` table for `articles_count` (754,219)
- If that table fails, it falls back to `count_vectorized_content()` (26,918 chunks)
- These numbers differ because `staging_sec_archive` contains article-level records, while `vectorized_sec_count` counts individual text chunks within filings

### 5. Ticker Search Returns Empty Results

- `GET /api/tickers/search?q=NVDA` returns `[]` (empty) despite NVDA being in the database
- **Cause**: The `search_tickers()` function searches `unified_staging` table for `u.target_ticker ILIKE '%NVDA%'`, but the PostgreSQL query may have a join issue or the table structure differs
- **Investigation needed**: Check `search_tickers()` in `crud.py` lines 25-70

### 6. Ticker "A" in Tracked Tickers

- `GET /api/tickers/tracked` returns a ticker with symbol "A" and name "A"
- This appears to be a placeholder/seed record in the database
- Should be filtered out or investigated

### 7. Mock Data Still Referenced in App.tsx

- `App.tsx` still imports and re-exports mock data: `import { TICKERS, NEWS_ARTICLES, ... } from "../mockData"`
- These are used for the landing page and fallback scenarios
- Not a bug, but worth noting for full migration

---

## 14. Developer Quick Reference

### SSH Access

```bash
# API VM
gcloud compute ssh isabellabutera@ftd-staging-api --zone us-west2-a --tunnel-through-iap

# Web VM
gcloud compute ssh isabellabutera@ftd-staging-web --zone us-west2-a --tunnel-through-iap

# PostgreSQL VM
gcloud compute ssh isabellabutera@ftd-postgres-vm --zone us-west2-a --tunnel-through-iap
```

### File Paths on VMs

| Path (API VM) | Purpose |
|---|---|
| `/home/isabellabutera/app/` | Backend code root |
| `/home/isabellabutera/app/app/` | Python package directory |
| `/home/isabellabutera/app/.venv/` | Python virtual environment |
| `/home/isabellabutera/app/version.json` | Deployment metadata |
| `/tmp/uvicorn.log` | API server logs |

| Path (Web VM) | Purpose |
|---|---|
| `/home/isabellabutera/frontend/dist/` | Frontend build output |
| `/etc/nginx/sites-enabled/staging` | nginx config |
| `/home/isabellabutera/version.json` | Deployment metadata |

### Service Management

```bash
# Check status
sudo systemctl status ftd-api.service

# Restart
sudo systemctl restart ftd-api.service

# Logs (follow)
sudo journalctl -u ftd-api.service -f

# Or tail log file
tail -50 /tmp/uvicorn.log
```

### Useful curl Commands

```bash
# Health (public)
curl https://bunch-length-classic-caring.trycloudflare.com/api/health

# Version (public)
curl https://bunch-length-classic-caring.trycloudflare.com/api/version

# Tracked tickers (public)
curl https://bunch-length-classic-caring.trycloudflare.com/api/tickers/tracked

# Dashboard stats (public)
curl https://bunch-length-classic-caring.trycloudflare.com/api/dashboard/stats

# Alerts (requires auth)
curl -H "Authorization: Bearer <token>" https://bunch-length-classic-caring.trycloudflare.com/api/alerts

# Ticker search (requires auth)
curl -H "Authorization: Bearer <token>" "https://bunch-length-classic-caring.trycloudflare.com/api/tickers/search?q=NVDA"

# SEC filing content (public, proxies to GCS or SEC.gov)
curl "https://bunch-length-classic-caring.trycloudflare.com/api/tickers/NVDA/filings/0001193125-15-165999/content?cik=0001048911"
```

### Test Data

The `tickers` table has all 494 tickers with `evidence_score=50.00` and `hype_score=50.00` — these are default values, not computed scores.

### Frontend Build Commands

```bash
# Build
npx vite build

# Dev server
npx vite

# The dev server runs at http://localhost:5173
# CORS is configured to allow localhost:5173
```

### Git Workflow

```bash
# Main branch
git checkout feature/frontend-modular-refactor

# Before making changes, commit current state
git add -A && git commit -m "checkpoint: description"

# Push to remote
git push origin feature/frontend-modular-refactor
```

### Git Tags (Recovery Points)

```bash
backup-before-55e179b5-revert    # Before reverting to mock data state
production-ready-backup           # Snapshot before final fixes
```

### Repo Split (from original monorepo)

The original `gcloud-bucket-data` repo was split into 3 GitHub repos:
1. **FTD-BE**: `Aquawile/FTD-BE` — Backend code (app/, tests/, scripts/)
2. **FTD-FE**: `Aquawile/FTD-FE` — Frontend prototype (context/figma_prototype/)
3. **ftd-cloud**: `Aquawile/ftd-cloud` — Infrastructure/deployment scripts

The split was done via `gh CLI` and all use the main `gcloud-bucket-data` directory for local development.

### Environment Variables on VMs

The backend reads env vars from:
1. systemd service file (`/etc/systemd/system/ftd-api.service`)
2. Shell environment (set by `scripts/start_app.sh`)
3. `.env` file (via python-dotenv, if present at `/home/isabellabutera/app/.env`)

For local development: copy `start_app.sh` and modify the defaults, or set env vars directly.
