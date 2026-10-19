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
├── tests/                        # unit (~190) + db_integration (~70, real Postgres in CI)
│   ├── test_api_endpoints.py     # API endpoint tests (auth, routes, response shapes)
│   └── test_user_sync.py         # User sync integration tests
├── scripts/
│   ├── start_app.sh              # Start uvicorn on the dev VM (staging uses systemd ftd-api)
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

1. **Client sees relational data; operations run on vectorized data; nothing leaves GCS + Postgres.** SEC filings are vectorized JSON in GCS (`ftd-vectorized-data`), mirrored chunk-for-chunk into Postgres `sec_vectorized_chunks` by the sync cron. SEC lookups, filing lists, elements and search query that mirror per request. Article and ticker counts come from the relational tables (`staging_sec_archive`, which is paused, and `tickers`).
   **Rules:** fetch only what the request needs, at request time, most recent first. No precomputed summary tables, no in-process or external caches, and no request may list or download the whole bucket.

2. **Firebase-only auth**: Firebase ID tokens only (project `ftd-2026`); see section 4.

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

### data-ingest-vm (e2-medium; the expensive one)

Started by Cloud Scheduler, stops itself when its job finishes:

| UTC | Scheduler | Job | Stops via |
|---|---|---|---|
| 21:55 | `start-price-vm-scheduler` | cron 22:00 `~/prices/run.sh` (Finnhub → `raw-data-strg/prices/`) | EXIT trap, ~22:09 |
| 03:30 | `sec-8k-daily-start` | startup-script (`sec/scripts/vm_startup.sh`) runs `/opt/sec-8k-ingestion` `src.main` (8-K delta scan, ~2 min) | `src.main` finally-block, then the script |
| 04:00 | `lakehouse-daily-pipeline` | **PAUSED** 2026-10-18: lakehouse feeds the paused relational tables | — |

- Safety net: `max-uptime-shutdown.service` powers the VM off 90 min after any boot (`sudo shutdown -c` to cancel while debugging).
- The startup script only runs SEC on a 03:xx boot (`FORCE_SEC=1` to test); on the 21:55 boot it does nothing so it can't stop the VM before the price fetch.
- The lakehouse `run.sh` no longer passes `--postgres`: it can never truncate relational tables.
- Deploy SEC code: tar `sec/` (no `.env`/`.venv`) → `/opt/sec-8k-ingestion`, keep the VM's `.env` (lookback 30 days), `pip install -r requirements.txt`.

### Service Account
- `github-actions-deploy@ftd2026.iam.gserviceaccount.com` (used in CI/CD workflows)

---

## 4. Authentication Flow

### Firebase only (project `ftd-2026`)

Accounts, passwords, email verification, password resets and sessions all live in Firebase.
The API never issues its own tokens (the internal-JWT login/register API was removed 2026-10-19).

1. User signs in with Firebase (email/password). "Remember me" picks Firebase persistence:
   checked = `browserLocalPersistence` (stays signed in on that browser until sign-out),
   unchecked = `browserSessionPersistence` (signed out when the browser closes).
2. Firebase refreshes the 1-hour ID token automatically; the frontend sends it on every call
   (`apiRequest()` and `fetchWithAuth()` both use `getIdToken()`, cached).
3. AuthMiddleware calls `validate_firebase_token_with_reason(token)`; anything Firebase rejects → 401.
4. `get_current_application_user` looks up (or on first sign-in creates, with the 9 default
   permissions) the PostgreSQL `users` row for that `firebase_uid`.
5. On load the app waits for Firebase to restore the session, so a signed-in user lands on the
   Dashboard instead of the login page.

### Auth Components

| File | Responsibility |
|---|---|
| `app/auth/middleware.py` | `AuthMiddleware` — intercepts every request, checks PUBLIC_PATHS, validates tokens |
| `app/auth/firebase_auth.py` | `validate_firebase_token_with_reason()` — verifies Firebase ID token |
| `app/auth/dependencies.py` | `get_current_application_user()` — resolves user from request state |
| `app/auth/user_sync.py` | `synchronize_user()` — creates/updates user in PostgreSQL from Firebase identity |

### PUBLIC_PATHS (no auth required)

```python
PUBLIC_PATHS = {
    "/health",
    "/version",
    "/auth/me",
    "/dashboard/stats",
    "/tickers/tracked",
}
# Plus SEC proxy pattern: /tickers/*/content (SEC_PROXY_PREFIX/SUFFIX)
```

No interactive API docs: `/docs`, `/redoc` and `/openapi.json` are disabled (research web app only,
the API is not offered publicly).

---

## 5. API Endpoints

### Public Endpoints (no auth)

| Method | Path | Description | Response Model |
|---|---|---|---|
| GET | `/health` | Health check + DB access counters | `{"status":"ok","db_access_counters":{},"db_access_detected":false}` |
| GET | `/version` | Deployment version metadata | `VersionMetadata` |
| GET | `/dashboard/stats` | Dashboard stats (articles, tickers, alerts, vectorized count) | `DashboardStats` |
| GET | `/tickers/tracked` | Tracked tickers list (`?symbol=NVDA` for one ticker; used by the ticker page header) | `list[TrackedTicker]` |
| GET | `/tickers/{ticker}/filings/{accession}/content` | SEC filing content proxy | HTMLResponse |

### Auth-Required Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/auth/me` | — | Firebase identity claims |
| GET | `/auth/me/user` | — | Application user (created on first sign-in) |
| GET | `/alerts` | `tickers.*` implied | User-specific alerts |
| GET | `/alerts/summary` | — | Unread count + newest unread alert (bell dot, Alerts nav badge, new-alert pop-up) |
| POST | `/alerts/read` | — | Mark all (or `alert_ids`) read |
| GET/POST | `/alerts/subscriptions` | — | The user's own subscriptions / create one (price_above, price_below, news, filing) |
| PATCH | `/alerts/subscriptions/{id}` | — | Pause/resume or change threshold (no delete) |
| GET | `/tickers/search?q=...` | `tickers.search` | Ticker search |
| GET | `/tickers/{ticker}/prices` | `tickers.prices` | Historical prices |
| GET | `/tickers/{ticker}/price-timeline?window_days=365` | `tickers.prices` | pandas-built daily series on a fixed 365-day window (`app/services/price_timeline.py`) |
| GET | `/tickers/{ticker}/news` | `tickers.news` | News articles |
| GET | `/tickers/{ticker}/timeline` | `tickers.timeline` | Timeline events |
| GET | `/tickers/{ticker}/filings` | `tickers.filings` | SEC filings list |
| GET | `/tickers/{ticker}/fiscal-year-end` | `tickers.fiscal_year_end` | Fiscal year end |
| GET | `/search?q=...` | `search.read` | Content search |
| GET | `/filings/{accession}/elements` | `filings.read` | Filing elements |
| GET | `/workspaces` | — | User workspaces |
| POST | `/workspaces` | — | Create workspace |
| GET | `/workspaces/{id}` | — | Workspace details (name, description, tickers, unread alerts, alert_on_filings) |
| PATCH | `/workspaces/{id}` | — | Rename, description, `alert_on_filings` (keeps a filing subscription on for each ticker) |
| DELETE | `/workspaces/{id}` | — | **Archive** (sets `archived_at`; hidden, never deleted) |
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
    current_price: Optional[float] = None   # latest staging_finnhub quote (snapshot only if strictly newer)
    change_percent: Optional[float] = None
    price_as_of: Optional[str] = None
    # name = tickers.name if it is a real name, else ticker_company_names, else the symbol

class DashboardStats(BaseModel):
    articles_count: int = 0        # news_articles_count + sec_filings_count (live, never frozen)
    news_articles_count: int = 0   # COUNT(DISTINCT url) on staging_gnews
    sec_filings_count: int = 0     # distinct accessions: staging_sec_archive UNION vectorized mirror
    tickers_count: int = 0         # COUNT DISTINCT from tickers table
    vectorized_sec_count: int = 0  # count_vectorized_content() — COUNT on sec_vectorized_chunks (SEC rows)
    # hype/evidence scores and the global alerts_count were removed (mock / not per-user)

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
  → _resolve_ticker_to_cik("NVDA")   [1 query: sec_vectorized_chunks path SEC/{form}/{CIK}/…/nvda-{date}.htm]
  → GROUP BY source_object for SEC/8-K/{CIK}/% and SEC/10-K/{CIK}/%   [sec_vectorized_chunks]
  → Returns FilingSummary rows, most recent first (~0.04s; no GCS reads)
```

### Dashboard Stats Flow

```
GET /api/dashboard/stats
  → dashboard.py: route_dashboard_stats()
  → count_vectorized_content()  → COUNT(*) on sec_vectorized_chunks WHERE source_object LIKE 'SEC/%' (26,918; ~6 ms)
  → crud.count_articles()       → news (distinct URLs in staging_gnews, 21,959) +
                                   filings (archive accessions via index skip scan UNION mirror accessions, 707)
  → query_dict("SELECT COUNT(DISTINCT symbol) FROM tickers")  → tickers_count (494)
  (whole endpoint ~0.13 s on the VM; indexes from migration 012)
```

### Ticker Tracked Data Flow

```
GET /api/tickers/tracked
  → tickers.py: route_get_tracked_tickers()
  → crud.py: get_tracked_tickers()
  → Reads from PostgreSQL: tickers table (name, sector, evidence/hype scores)
  → LEFT JOIN latest staging_finnhub quote per symbol (_LATEST_PRICES);
    current_price / change_percent / price_as_of come from whichever is newer
  → Returns TrackedTicker objects (494 total)
```

### Data Inventory: Relational vs Vectorized (as of 2026-10-15)

Every daily feed lands raw in `raw-data-strg`, then fans out to two stores:
**relational** (PostgreSQL, structured rows the API filters/sorts) and
**vectorized** (`ftd-vectorized-data`, JSON with 384-dim MiniLM embeddings per text chunk).

```
raw-data-strg/prices/{date}/data.jsonl ──► staging_finnhub ──► tickers (price snapshot)
             (22:09 UTC daily)          └► ftd-vectorized-data/prices/{date}/data.json
raw-data-strg/gnews/{date}/batch_NNN.json ► staging_gnews
             (~00:00 UTC daily; queries: company name OR ticker, see known issue #10)
                                         └► ftd-vectorized-data/gnews/{date}/batch_NNN.json
raw-data-strg/SEC/{form}/{CIK}/{acc}/*.htm ► ftd-vectorized-data/sec-{8k,10k}/{CIK}/{acc}/{ticker}-{date}.json
                                          (SEC content is NOT in live Postgres tables)
ftd-vectorized-data/** ──(scripts/sync_vectorized_to_postgres.py)──► sec_vectorized_chunks (mirror)
```

**Relational (PostgreSQL `ftd_lakehouse_staging`)**

| Table | Holds | Fed by | Latest | Read by (API → webapp) |
|---|---|---|---|---|
| `tickers` | 494 symbols: name, sector, scores, price snapshot | `sync_recent_relational.py` refreshes price cols | 2026-10-15 | `/tickers/tracked` (Dashboard, Search, Alerts, Workspace, TickerDashboard header), `/tickers/search`, `/dashboard/stats` |
| `staging_finnhub` | Daily quote per symbol (current, open/high/low, change, %) | raw `prices/` | 2026-10-15 | `/tickers/{t}/prices` (TickerDashboard financials), `/tickers/{t}/timeline`, `/tickers/tracked` |
| `staging_gnews` | News article rows per queried symbol | raw `gnews/` | 2026-10-14 (GNews free plan has 12h delay) | `/tickers/{t}/news` (TickerDashboard news), `/tickers/{t}/timeline`, `/search?source=gnews` |
| `staging_sec_archive` | 754,219 historical SEC elements (frozen) | lakehouse parquet (Jul 2026) | static | `/dashboard/stats` `articles_count` |
| `fiscal_parameters` | Fiscal year end per CIK | lakehouse parquet | static | `/tickers/{t}/fiscal-year-end` |
| `alerts`, `workspaces`, `workspace_tickers`, `users`, `user_permissions`, `permissions`, `api_usage_log` | App/user state | the app itself | live | `/alerts`, `/workspaces`, `/users`, audit |
| `unified_staging` (VIEW) | **Always empty** (`SELECT … FROM unified_staging_archive WHERE false`) | — | — | Not read anymore; `crud._RELATIONAL_UNIFIED` unions finnhub + gnews instead |
| `staging_sec` (VIEW) | Deprecated SEC view | — | — | Only deprecated crud functions (increment DB-access counters) |

**Vectorized (GCS `ftd-vectorized-data`)**

| Prefix | Files | Holds | Latest | Read by (API → webapp) |
|---|---|---|---|---|
| `sec-10k/{CIK}/…` | 495 | 10-K chunks + embeddings, `sec_metadata` | filing 2026-06-22 | `/tickers/{t}/filings` (TickerDashboard filings), `/filings/{acc}/elements`, `/tickers/{t}/timeline` (sec), `/search`, `/dashboard/stats` `vectorized_sec_count` |
| `sec-8k/{CIK}/…` | 212 | 8-K chunks + embeddings | filing 2026-06-26 | same as above |
| `gnews/{date}/…` | 1,498 | News batch text + embeddings | 2026-10-15 | Not served by the API (mirrored to `sec_vectorized_chunks`) |
| `prices/{date}/…` | 16 | Price text + embeddings | 2026-10-15 | Not served by the API (mirrored to `sec_vectorized_chunks`) |

SEC endpoints read the `sec_vectorized_chunks` mirror per request (scoped by ticker, accession or keyword; most recent first).
The mirror is refreshed incrementally by the sync cron, so a newly vectorized filing appears after the next run (22:20 / 00:20 UTC).
Raw filing HTML (`/tickers/{t}/filings/{acc}/content`) is read from `raw-data-strg` under that one accession's prefix.
Measured on staging 2026-10-16: every data endpoint makes 0 GCS list/download calls; SEC search 12s → 0.13s, filings/timeline/elements 0.01–0.04s.

**Keeping data current (cron on `ftd-staging-api`, UTC)**: `scripts/sync_all_recent.sh` runs at
22:20 (after raw prices land ~22:09) and 00:20 (after GNews lands ~00:00). It takes PG* env from
the `ftd-api` systemd unit and runs, independently:

1. `scripts/sync_recent_relational.py` (on VM: `~/prices/`): incremental, idempotent, insert-only.
   Reads raw date folders since the newest date already in Postgres, inserts quotes not already
   stored (same ticker, day and quote timestamp are skipped; nothing is deleted), inserts new news
   rows, refreshes the `tickers` price snapshot. A missed run is caught up by the next one.
2. `scripts/sync_vectorized_to_postgres.py` (on VM: `~/app/scripts/`): mirrors vectorized files
   updated since the newest `vectorized_at` in `sec_vectorized_chunks` (`--full` rescans everything).
3. `scripts/evaluate_alert_subscriptions.py` (on VM: `~/app/scripts/`): last, because ticker data
   only changes in steps 1–2. Checks each active `alert_subscriptions` row against
   `alert_subscription_state` and inserts into `alerts` only when the watched value changed
   (`app/services/alert_evaluator.py`). The web app shows them via `/alerts/summary`.

4. `scripts/check_data_freshness.py` (read-only): prices vs the last trading day, news and vectorized ages;
   its table is written to the sync log. The same check runs in GitHub Actions on every push to `staging`
   (`.github/workflows/data-freshness.yml`; opens `incident/data-freshness-<date>` if behind). GitHub only
   schedules workflows on the default branch (`main` = production, not used), hence the daily run on the VM.
   Deploys install all these scripts (deploy.yml, after a healthy API deploy).

The crontab also has `@reboot sleep 120 && ~/prices/sync_all_recent.sh`: the VMs are often
stopped overnight, and cron does not replay missed runs, so a boot catches up whatever was missed.
The pipeline does not ship these scripts; copy them to the VM by hand after changing them.

Log: `~/prices/sync_all_recent.log`. API endpoints need no cache busting: nginx doesn't cache
`/api/`, and the app only caches SEC filing HTML, which never changes once filed.

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

Set in `/etc/systemd/system/ftd-api.service` (the only way staging runs the API; `scripts/start_app.sh` is for the dev VM):

| Variable | Value | Description |
|---|---|---|
| `PGHOST` | `10.168.0.3` | PostgreSQL VM internal IP |
| `PGPORT` | `5432` | PostgreSQL port |
| `PGDATABASE` | `ftd_lakehouse_staging` | Database name |
| `PGUSER` | `ftd_app` | Database user |
| `PGPASSWORD` | `5Ou+BkyuQT3izP72219jMLy2AobRdI3f` | Database password |
| `FIREBASE_PROJECT_ID` | `ftd-2026` | Firebase project |
| `FIREBASE_AUTH_ENABLED` | `true` | Enable Firebase auth |
| `JWT_SECRET_KEY` / `JWT_EXPIRATION_MINUTES` | — | **Unused** since 2026-10-19 (internal JWT removed); can be dropped from the unit |
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
| `DashboardPage.tsx` | Dashboard with stats, top movers, recent alerts. Top Movers = the 5 tracked tickers with the largest absolute `change_percent` (latest Finnhub quote's daily % change) | Yes (getTrackedTickers, getAlerts) |
| `AlertsPage.tsx` | Alerts list with filtering | Yes (useAlerts hook → /api/alerts) |
| `TickerDashboard.tsx` | Single ticker detail page | Yes (getTrackedTickers, apiRequest for prices/news/filings, `PriceTimeline` chart) |
| `components/PriceTimeline.tsx` | 365-day price chart (Recharts) | Yes (`/tickers/{t}/price-timeline`) |
| `SearchPage.tsx` | Ticker search + autocomplete | Yes (useTickerSearch hook → /api/tickers/search) |
| `src/archive/` | **Archived 2026-10-16**: pages and sections showing data with no API behind it (hype/evidence scores, Timeline, Filings, Community, Comparison, Chat, Admin, Legacy landing). Not built or routed. See `src/archive/README.md` | No |
| `WorkspaceDetailPage.tsx` | Workspace detail view | Yes (workspace hooks) |

### Frontend API Client (`src/api/index.ts`)

```typescript
// Auth-aware fetch (for Firebase-authenticated endpoints)
export async function apiRequest(path, firebaseUser, options?): Promise<Response>
  → Gets Firebase ID token, adds Authorization: Bearer header

// Same, for helpers that don't receive firebaseUser
async function fetchWithAuth<T>(endpoint, options?): Promise<T>
  → firebaseAuth.currentUser.getIdToken() (cached), adds Bearer header when signed in
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

### Price Timeline Chart

`GET /tickers/{t}/price-timeline` reindexes the ticker's `staging_finnhub` quotes onto a
365-day calendar with pandas. While history is under 365 days, the window starts at the first
quote (2026-07-02) and runs forward, so the chart fills in as each nightly sync adds a day.
After that it becomes a rolling 365-day window. Days without a quote (weekends, holidays,
future days) are left empty and never interpolated. The chart bridges weekend gaps visually
(`connectNulls`) and shows a fill-progress bar.

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
| Vectorized data | `app/services/vectorized_gcs.py` | Request-scoped SEC reads from `sec_vectorized_chunks`; raw HTML from `raw-data-strg` |
| Audit logging | `app/services/audit.py` | Logs API requests + SEC proxy access |
| Data service | `app/services/data_service.py` | Orchestrates data operations |
| User fingerprint | `app/services/user_fingerprint.py` | Extracts user identity from request |
| User service | `app/services/user_service.py` | User lookup operations |

### Key Service Functions (vectorized_gcs.py)

```python
# Resolve ticker symbol to SEC CIK
_resolve_ticker_to_cik(ticker: str) -> str | None
  → One query: CIK from mirror paths SEC/{form}/{CIK}/…/{ticker}-{YYYYMMDD}.htm (572 of 707 files carry a ticker)

# List filings for a ticker
list_filings_for_ticker(ticker: str) -> list[FilingSummary]
  → Resolve CIK → GROUP BY file in the mirror → most recent first

# Get filing elements/chunks
get_filing_elements_by_accession(accession_number: str) -> list[FilingElement]
  → Indexed lookup on accession_number (dashed or undashed) → chunks in order

# Count total vectorized content elements
count_vectorized_content() -> int
  → One COUNT(*) of SEC rows in the mirror

# Keyword search over SEC chunks
search_vectorized_content(keyword, limit) -> list[SearchResult]
  → ILIKE on text_preview (wildcards escaped), ORDER BY filing_date DESC, LIMIT

# Serve SEC filing content
get_filing_content_from_gcs(ticker, accession, cik) -> tuple[bytes, str, bool]
  → Looks in raw-data-strg bucket for .htm files
  → Falls back to SEC.gov if not found

# Get timeline events
get_timeline_from_gcs(ticker, start, end, limit, offset) -> list[TimelineEvent]
  → Resolve CIK → first chunk of each file in the date range, most recent first
```

### Middleware Order (important!)

1. **CORS** (`CORSMiddleware`) — first, handles OPTIONS
2. **Auth** (`AuthMiddleware`) — validates tokens, sets request.state
3. **Audit** (`AuditLogMiddleware`) — wraps request/response for logging

---

## 10. Deployment

### How staging is deployed

**Normal path: push to the `staging` branch.** `Deploy to GCP` (`.github/workflows/deploy.yml`) waits for CI, then runs:

1. **Migrations:** applies every `app/auth/migrations/NNN_*.sql` not recorded in `schema_migrations`, each in one transaction (`ON_ERROR_STOP`) together with its ledger row. Legacy 001–005 are recorded, not re-run, when their schema exists.
2. **Backend:** tarball → unpack to `~/app/.release` → `pip install` → swap into `~/app/app` (previous kept as `~/app/app.prev`) → `sudo systemctl restart ftd-api` → health check `:8080/health` → auto-rollback if unhealthy → write `~/version.json` → verify `/version` reports the SHA.
3. **Web:** `vite build` → tarball → `~/frontend/dist.new` → swap into `~/frontend/dist` (previous kept as `dist.prev`) → `nginx -t` + reload → health check → rollback on failure → write `~/version.json`.

**Layout the VM expects (don't deviate):**
- API runs **only** as systemd `ftd-api.service`: `uvicorn app.main:app` on **:8080**, `WorkingDirectory=/home/isabellabutera/app`, `Restart=always`. Never `pkill uvicorn` or start a second copy (`scripts/start_app.sh` is for the dev VM only).
- Backend code lives in **`/home/isabellabutera/app/app/`**. Nothing else belongs at the top of `~/app/` except `.venv/` and `scripts/`.
- Deployment metadata is **`/home/isabellabutera/version.json`** on each VM (read per request by `/version`).

### Manual deploy (fallback only; mirrors the pipeline)

```bash
# Backend: swap the whole package dir, then restart the service
tar --exclude='__pycache__' -czf /tmp/ftd-release.tgz app requirements.txt
gcloud compute scp /tmp/ftd-release.tgz isabellabutera@ftd-staging-api:/tmp/ --zone us-west2-a --tunnel-through-iap
gcloud compute ssh isabellabutera@ftd-staging-api --zone us-west2-a --tunnel-through-iap --command 'set -euo pipefail
  cd ~/app && rm -rf .release && mkdir .release && tar -xzf /tmp/ftd-release.tgz -C .release
  .venv/bin/pip install --quiet -r .release/requirements.txt
  rm -rf app.prev && mv app app.prev && mv .release/app app && rm -rf .release
  sudo systemctl restart ftd-api.service && sleep 5 && curl -s localhost:8080/health'
# then write ~/version.json (commit_sha, branch, deployed_at, environment) only if healthy

# Frontend: replace dist as a whole (never copy dist/ into dist/: it nests)
(cd context/figma_prototype && npx vite build && tar -czf /tmp/ftd-web.tgz -C dist .)
gcloud compute scp /tmp/ftd-web.tgz isabellabutera@ftd-staging-web:/tmp/ --zone us-west2-a --tunnel-through-iap
gcloud compute ssh isabellabutera@ftd-staging-web --zone us-west2-a --tunnel-through-iap --command 'set -euo pipefail
  cd ~/frontend && rm -rf dist.new && mkdir dist.new && tar -xzf /tmp/ftd-web.tgz -C dist.new
  rm -rf dist.prev && mv dist dist.prev && mv dist.new dist && sudo nginx -t && sudo systemctl reload nginx'
```

Rollback: `mv app app.bad && mv app.prev app && sudo systemctl restart ftd-api` (or `dist.prev` → `dist` on the web VM).

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

**Test count**: ~190 unit tests + ~70 `db_integration` tests. CI runs the db tests against a throwaway
`postgres:15` built by `tests/schema/setup_test_db.sh` (staging schema + pending migrations + seed), as
`ftd_app`, with `REQUIRE_DB=1` (a skipped db test fails CI). Frontend: `npx tsc --noEmit` is clean
(`src/archive` and `src/legacy` are excluded).

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

### PostgreSQL Tables (17 base tables + 2 views, verified 2026-10-15)

| Table | Purpose | Rows |
|---|---|---|
| `tickers` | Symbols, names, sectors, scores, price snapshot (no `cik` column) | 494 |
| `staging_finnhub` | Daily price quotes | 35,239 |
| `staging_gnews` | News articles | 106,924 |
| `staging_sec_archive` | Historical SEC elements (frozen) | 754,219 |
| `unified_staging_archive` | Empty | 0 |
| `sec_vectorized_chunks` | Mirror of `ftd-vectorized-data` (SEC + gnews + prices) | 35,757 |
| `fiscal_parameters` | Fiscal year end per CIK | 477 |
| `users` | Application users | 8 |
| `user_permissions` / `user_permissions_index` | Permission assignments | 37 / 54 |
| `permissions` | Permission definitions | 9 |
| `workspaces` / `workspace_tickers` | User workspaces | 1 / 1 |
| `alerts` / `alert_subscriptions` | User alerts | 0 / 2 |
| `api_usage_log` | Audit log | 224 |
| `schema_migrations` | Applied migrations | 7 |
| `unified_staging` (VIEW) | Always empty — see Data Inventory | 0 |
| `staging_sec` (VIEW) | Deprecated | — |

There is no `latest_price_data` table; latest prices come from `staging_finnhub`.

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

### 5. Ticker Search Returns Empty Results (FIXED 2026-10-15)

- **Cause**: `unified_staging` is a view defined `WHERE false`, so every query on it returned nothing (search, timeline finnhub/gnews, non-SEC content search, and step 2 of ticker→CIK resolution).
- **Fix**: `search_tickers()` reads `tickers`; timeline and content search read `crud._RELATIONAL_UNIFIED` (`staging_finnhub` UNION ALL `staging_gnews`). `crud.get_dashboard_stats()` still references the view but no route calls it.

### 6. Ticker "A" in Tracked Tickers (RESOLVED 2026-10-18)

- "A" is Agilent Technologies. 484 of 494 `tickers` rows store the symbol as `name`; the API now
  shows the company name from `ticker_company_names` (migration 013, `scripts/load_company_names.py`:
  10-K names from `SEC/config/company_names.json`, then SEC's `company_tickers.json` for the rest).
  `tickers.name` itself is never overwritten.

### 7. Mock Data Still Referenced in App.tsx

- `App.tsx` still imports and re-exports mock data: `import { TICKERS, NEWS_ARTICLES, ... } from "../mockData"`
- These are used for the landing page and fallback scenarios
- Not a bug, but worth noting for full migration

### 8. Relational Data Stopped Loading on 2026-09-17 (backfilled 2026-10-15)

- The API VM cron `20 22 * * * ~/prices/lakehouse_run.sh` exits immediately every night: cron has no `PGPASSWORD`, and `lakehouse_run.py` imports `src.*` from `~/app/sec`, which doesn't exist. It also only loaded prices, not news.
- Backfilled 2026-09-18 → 2026-10-15 with `scripts/sync_recent_relational.py` (11,778 price rows, 97,084 news rows, 492 ticker snapshots).
- **Fixed 2026-10-16**: crontab now runs `~/prices/sync_all_recent.sh` at 22:20 and 00:20 UTC (see Data Inventory → Keeping data current). The old `lakehouse_run.sh` line is kept commented out; previous crontab backed up in `~/backups/`. Verified under a cron-like empty environment.
- The 9,840 news rows from the old loader (all `ingest_date = 2026-09-18`) contain 1,580 duplicate (ticker, url, date) groups. Rows inserted by the sync script have no duplicates.

### 9. `target_cik` Is Misaligned in Staging Tables

- In `staging_finnhub` / `staging_gnews`, `target_cik` is wrong for ~428 of 447 symbols (e.g. AAPL → `0000006951`, correct is `0000320193`; NVDA → `0000029989`, correct is `0001045810`). It looks like an off-by-N zip in the lakehouse ticker→CIK mapping.
- The correct CIKs are the folder names in `ftd-vectorized-data/sec-*/{CIK}/`. `_resolve_ticker_to_cik` reaches that path because step 1 (`tickers.cik`) doesn't exist and step 2 (`unified_staging`) is empty. **Do not resolve CIKs from the staging tables** until they're corrected.
- `/tickers/search` returns `cik: ""` for this reason.

### 10. News Attribution Is Per GNews Query Batch

- Each GNews batch covers ~5 tickers, and every article in it is filed under all of them. A ticker's news can therefore include articles about the others in its batch. **This is deliberate:** articles can be indirectly related without naming the company, so nothing is filtered or deleted.
- **Until 2026-10-16** queries were `"$MMM" OR "$AOS" …`. GNews ignores `$`, so bare tickers matched unrelated text (e.g. "NOC" certificates filed under NVDA's batch). Only ~2% of stored rows name their ticker or company (`scripts/news_attribution_report.py`, read-only).
- **Since 2026-10-16 (gnews-ingest v45)** each ticker is searched by full company name **and** ticker: `"3M" OR "MMM" OR "A. O. Smith" OR "AOS" …` (`gnews/queries.py`). Names come from `gs://raw-data-strg/SEC/config/company_names.json` (464 of 500 tickers; rebuild with `scripts/build_company_names.py` from 10-K `dei:EntityRegistrantName`). Still 100 requests/day (GNews free-plan limit), 5 tickers per query, each query ≤ 200 chars. Each batch file now also stores its `tickers`, which the sync reads (`batch_tickers()`; falls back to `"$TICK"` for older files).
- `sync_recent_relational.py --strict-attribution` exists but is **off**; the nightly cron keeps every fetched article.
- The gnews-ingest function is deployed only by the dev pipeline (`rawdataingestion` push with "gnews"/"deploy" in the message) or by hand with the same flags as `deploy.yml` plus `COMPANY_NAMES_GCS_PATH`.

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
| `/home/isabellabutera/app/` | Service working dir: holds only `app/`, `.venv/`, `scripts/` (+ `app.prev/` after a deploy) |
| `/home/isabellabutera/app/app/` | Python package the service imports (deployed code) |
| `/home/isabellabutera/app/.venv/` | Python virtual environment |
| `/home/isabellabutera/app/scripts/` | `sync_vectorized_to_postgres.py` (run by cron) |
| `/home/isabellabutera/prices/` | `sync_all_recent.sh`, `sync_recent_relational.py` (cron) |
| `/home/isabellabutera/version.json` | Deployment metadata (served by `/version`) |
| `/home/isabellabutera/backups/` | Pre-deploy backups and moved stale files |
| `journalctl -u ftd-api.service` | API server logs |

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
2. Shell environment (`scripts/start_app.sh`, dev VM only; staging uses the systemd unit)
3. `.env` file (via python-dotenv, if present at `/home/isabellabutera/app/.env`)

For local development: copy `start_app.sh` and modify the defaults, or set env vars directly.
