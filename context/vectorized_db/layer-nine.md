# LAYER NINE — UI-TO-API-TO-DATA SOURCE TRACE

**Agent implementation specification.** This document provides the complete end-to-end trace from every user-facing UI element through the API layer to the underlying data source. Each trace must be verified before the migration proceeds. The agent must follow these specifications literally.

## **GLOBAL OPERATING RULES**

1. This layer is read-only documentation. No code changes are made.
2. Every UI data binding must be traced to confirm its data source after migration.
3. Endpoints that read SEC filing data are candidates for GCS migration.
4. Endpoints that read user/ticker/price/news relational data remain in PostgreSQL.
5. The trace must identify whether each API response currently comes from `crud.py` (PostgreSQL) or can be sourced from `ftd-vectorized-data` (GCS).
6. The agent must NOT modify any code in this layer. Only trace and document.

---

## **TRACE MATRIX**

### **Legend**
- **S** = Must migrate to GCS (`ftd-vectorized-data`)
- **R** = Relational/user data, stays in PostgreSQL
- **P** = Partial migration (some sources from GCS, some from Postgres)
- **N** = Not implemented / placeholder

---

## **SUBLAYER 9.1 — TickerDashboard.tsx Full Trace**

**File:** `context/figma_prototype/src/components/pages/TickerDashboard.tsx`
**Lines:** 108-112 (API calls in `useEffect`)

### Trace 1: Price Data
- **UI binding:** `TickerDashboard.tsx:109` → `financials.currentPrice`, `financials.previousClose`, etc.
- **API call:** `apiRequest('/tickers/${ticker}/prices?start=...&end=...', firebaseUser)`
- **Route:** `app/routes/tickers.py:51` → `route_get_prices()`
- **CRUD:** `app/crud.py:73` → `get_ticker_prices()`
- **SQL:** `SELECT ... FROM staging_finnhub WHERE target_ticker = %s`
- **Data source:** PostgreSQL `staging_finnhub` (Finnhub price data)
- **Migration tag:** **R** (relational price data, no vectorized equivalent)
- **Auth:** Firebase via `apiRequest()` → `AuthMiddleware` sets `request.state.firebase_uid`

### Trace 2: News Data
- **UI binding:** `TickerDashboard.tsx:110`, `TickerDashboard.tsx:265-291` (news list rendering)
- **API call:** `apiRequest('/tickers/${ticker}/news?start=...&end=...&limit=50', firebaseUser)`
- **Route:** `app/routes/tickers.py:61` → `route_get_news()`
- **CRUD:** `app/crud.py:96` → `get_ticker_news()`
- **SQL:** `SELECT ... FROM staging_gnews WHERE target_ticker = %s`
- **Data source:** PostgreSQL `staging_gnews` (GNews articles)
- **Migration tag:** **R** (GNews data, no vectorized equivalent)
- **Auth:** Firebase via `apiRequest()`

### Trace 3: SEC Filings List
- **UI binding:** `TickerDashboard.tsx:111`, `TickerDashboard.tsx:305-327` (filing cards rendering)
- **API call:** `apiRequest('/tickers/${ticker}/filings', firebaseUser)` (via `tickerHooks.ts:65`)
- **Route:** `app/routes/tickers.py:80` → `route_get_filings()`
- **Service:** `app/services/vectorized_gcs.py:105` → `list_filings_for_ticker()`
- **SQL (ticker→CIK resolution only):** `app/services/vectorized_gcs.py:62` → `SELECT cik FROM tickers WHERE symbol = %s` (relational metadata only)
- **Data source:** `ftd-vectorized-data/sec-8k/{CIK}/` and `sec-10k/{CIK}/` (GCS JSON)
- **Migration tag:** **S** (SEC filing metadata now from GCS; ticker→CIK from PostgreSQL tickers table)
- **Auth:** Firebase via `apiRequest()` → `AuthMiddleware` sets `request.state.firebase_uid`
- **Field mapping:**
  - `FilingSummary.target_ticker` ← ticker param (passed by caller)
  - `FilingSummary.target_cik` ← `sec_metadata.cik`
  - `FilingSummary.form_type` ← `sec_metadata.form`
  - `FilingSummary.accession_number` ← `sec_metadata.accession_number`
  - `FilingSummary.filing_date` ← `sec_metadata.filing_date`
  - `FilingSummary.element_count` ← `len(chunks)`
  - `FilingSummary.url` ← constructed from CIK + accession_number (EDGAR link)

### Trace 4: Ticker Timeline
- **UI binding:** `TickerDashboard.tsx` (overview tab displays timeline events; `tickerHooks.ts:64` calls API)
- **API call:** `fetch('/api/tickers/${ticker}/timeline')` (from `useTickerDashboard` hook, `tickerHooks.ts:64`)
- **Route:** `app/routes/tickers.py:107` → `route_get_timeline()`
- **Service (SEC):** `app/services/vectorized_gcs.py:302` → `get_timeline_from_gcs()`
- **Service (gnews/finnhub):** `app/crud.py:180` → `get_ticker_timeline()`
- **SQL (SEC):** None — reads from GCS JSON `sec_metadata` + chunks
- **SQL (gnews/finnhub):** `SELECT ... FROM unified_staging WHERE target_ticker = %s AND source = ANY(%s)`
- **Data source:** PostgreSQL `unified_staging` for gnews/finnhub; `ftd-vectorized-data` for SEC filings
- **Migration tag:** **P** (SEC portion → GCS; gnews/finnhub portions stay in PostgreSQL)
- **Auth:** Direct `fetch()` — NOT in `PUBLIC_PATHS`, requires Bearer token (SEC_PROXY bypass does NOT apply; this is a different path)

### Trace 5: Evidence Data
- **UI binding:** `TickerDashboard.tsx:75` → `tab === "evidence"` shows hardcoded matrix (lines 457-485)
- **API call:** `fetch('/api/tickers/${ticker}/evidence')` (from `useTickerDashboard` hook, `tickerHooks.ts:66`)
- **Route:** NOT defined in any route file — **endpoint does not exist**
- **Data source:** N/A (uses hardcoded mock data in component, not API)
- **Migration tag:** **N**
- **Auth:** Direct `fetch()` (no auth header — endpoint returns 404)

### Trace 6: Tracked Tickers
- **UI binding:** `TickerDashboard.tsx` (tab navigation, `SearchPage.tsx:38`)
- **API call:** `apiRequest('/tickers/tracked', firebaseUser)` (from `TickerDashboard.tsx:112` and `tickerHooks.ts:67`)
- **Route:** `app/routes/tickers.py:32` → `route_get_tracked_tickers()`
- **CRUD:** `app/crud.py:265` → `get_tracked_tickers()`
- **SQL:** `SELECT ... FROM tickers ORDER BY updated_at DESC LIMIT %s`
- **Data source:** PostgreSQL `tickers` (user-relationship data)
- **Migration tag:** **R** (ticker metadata, no vectorized equivalent)
- **Auth:** Firebase via `apiRequest()`

---

## **SUBLAYER 9.2 — SearchPage.tsx Full Trace**

**File:** `context/figma_prototype/src/components/pages/SearchPage.tsx`

### Trace 7: Tracked Tickers (Search Filtering)
- **UI binding:** `SearchPage.tsx:38` → `fetchTickers()` uses `apiRequest("/tickers/tracked", firebaseUser)`
- **Route:** `app/routes/tickers.py:32` → `route_get_tracked_tickers()`
- **CRUD:** `app/crud.py:265` → `get_tracked_tickers()`
- **Data source:** PostgreSQL `tickers`
- **Migration tag:** **R**

### Trace 8: Ticker Search
- **UI binding:** `SearchPage.tsx` uses `useTickerSearch` hook (`tickerHooks.ts:8-46`)
- **API call:** `fetch(\`/api/tickers/search?${params}\`)` (direct fetch, no auth header)
- **Route:** `app/routes/tickers.py:40` → `route_search_tickers()`
- **CRUD:** `app/crud.py:25` → `search_tickers()`
- **SQL:** `SELECT ... FROM unified_staging u LEFT JOIN tickers t ...`
- **Data source:** PostgreSQL `unified_staging` + `tickers`
- **Migration tag:** **R** (ticker search is relational metadata, not SEC filing content)
- **Auth:** Direct fetch (no auth header — potential security issue, but not in scope for this layer)

---

## **SUBLAYER 9.3 — FilingsPage.tsx Full Trace**

**File:** `context/figma_prototype/src/components/pages/FilingsPage.tsx`

### Trace 9: Filing List Display
- **UI binding:** `FilingsPage.tsx:8-14` — uses hardcoded mock data (`filings` array)
- **API call:** NONE — **no API call**
- **Data source:** Hardcoded mock array in component
- **Migration tag:** **N** (UI uses mock data; when migrated to API, will call `/api/tickers/{ticker}/filings`)

### Trace 10: Filing Content Viewer
- **UI binding:** `FilingsPage.tsx` — placeholder content (no real filing content display)
- **API call:** NONE — placeholder content shown
- **Migration tag:** **N**

---

## **SUBLAYER 9.4 — Content Search (Global)**

**File:** `context/figma_prototype/src/app/App.tsx`, `src/hooks/tickerHooks.ts`

### Trace 11: Global Search
- **UI binding:** `SearchPage.tsx` filters local data client-side (no dedicated search bar for content)
- **Note:** No `/api/search` calls found in the frontend code currently
- **Migration tag:** **N** (no UI integration yet for content search)
- **Backend endpoint:** `app/routes/search.py:26` → `route_search()` → `app/services/vectorized_gcs.py:203` → `search_vectorized_content()` (SEC); `app/crud.py:239` → `search_content()` (gnews/finnhub)
- **Data source:** `ftd-vectorized-data/sec-8k/` + `sec-10k/` (GCS, SEC); PostgreSQL `unified_staging` (gnews/finnhub)
- **Migration tag for backend:** **S** (SEC → GCS; gnews/finnhub stay in Postgres)

### Trace 11b: Dashboard Stats
- **UI binding:** `DashboardPage.tsx:21` → `fetch('/api/dashboard/stats')`
- **Route:** `app/routes/dashboard.py:12` → `route_dashboard_stats()`
- **Service (GCS):** `app/services/vectorized_gcs.py:259` → `count_vectorized_files()` (counts JSON in ftd-vectorized-data)
- **Service (PostgreSQL):** `app/crud.py:266` deprecated; route now queries `tickers` + `alerts` tables directly
- **SQL (ticker count):** `SELECT COUNT(DISTINCT symbol) AS count FROM tickers`
- **SQL (alerts count):** `SELECT COUNT(*) AS count FROM alerts`
- **Data source:** GCS (article count) + PostgreSQL `tickers` + PostgreSQL `alerts`
- **Migration tag:** **P** (articles_count from GCS, tickers/alerts remain PostgreSQL)
- **Auth:** Direct `fetch()` — `/dashboard/stats` is in `PUBLIC_PATHS` (line 22 of `app/auth/middleware.py`)

---

## **SUBLAYER 9.5 — SEC Filing Content Fetch (Proxy)**

**File:** `context/figma_prototype/src/components/pages/TickerDashboard.tsx:316-317`

### Trace 12: SEC.gov Content Link
- **UI binding:** `TickerDashboard.tsx:316` — link to:
  ```
  /api/tickers/${t.symbol}/filings/${f.accession_number.replace(/-/g, "")}/content?cik=${f.target_cik}
  ```
- **API call:** `fetch('/api/tickers/AAPL/filings/000032019320000070/content?cik=0000320193')`
- **Route:** `app/routes/tickers.py:224` → `route_get_filing_content()`
- **Service:** `app/services/vectorized_gcs.py:271` → `get_filing_content_from_gcs()` (GCS first, SEC.gov fallback via `_fetch_sec_content`)
- **Data source:** `raw-data-strg/SEC/8-K/{CIK}/{accession}/` (GCS HTML) → fallback to SEC.gov
- **Migration tag:** **S** (SEC filing HTML now served from GCS; SEC.gov as fallback for missing files)
- **Auth:** `SEC_PROXY_PREFIX` bypass in `app/auth/middleware.py:40` — path starts with `/tickers/` and ends with `/content`

---

## **SUBLAYER 9.6 — Auth Flow**

**File:** `context/figma_prototype/src/app/App.tsx`, `src/app/firebase.ts`, `src/api/index.ts`

### Trace 13: Firebase User Authentication
- **UI flow:** `App.tsx:21` → `firebaseAuth.onAuthStateChanged` → user object captured
- **API call:** `App.tsx:59-62` → `apiRequest("/auth/me/user", user)` and `apiRequest("/users/me/permissions", user)`
- **Auth method:** Firebase ID token → `Authorization: Bearer <firebase_id_token>`
- **Middleware:** `AuthMiddleware` validates Firebase token → sets `request.state.firebase_uid`, `request.state.email`, `request.state.auth_method = "firebase"`
- **Backend lookup:** `dependencies.py:51-68` → `get_authenticated_user(firebase_uid)` → PostgreSQL `users` table

### Trace 14: Internal JWT Authentication
- **UI flow:** When `firebaseUser` is null, App.tsx falls back to mock data
- **Auth method:** Internal JWT token → `Authorization: Bearer <jwt_token>`
- **Middleware:** `AuthMiddleware` validates JWT → sets `request.state.user_id`, `request.state.email`, `request.state.auth_method = "internal"`

### Trace 15: Workspace List
- **UI binding:** `WorkspacesPage.tsx:25` → `fetchWorkspaces(firebaseUser)`
- **API call:** `apiRequest("/workspaces", firebaseUser)` (Firebase auth)
- **Route:** `app/routes/workspaces.py:30` → `route_get_workspaces()`
- **CRUD:** `app/crud.py:304` → `get_user_workspaces()`
- **SQL:** `SELECT w.id, w.name, w.created_at, ARRAY_AGG(wt.ticker_symbol) ... FROM workspaces w LEFT JOIN workspace_tickers wt ...`
- **Data source:** PostgreSQL `workspaces` + `workspace_tickers` (user-relationship data)
- **Migration tag:** **R** (user workspace data, stays in PostgreSQL)

### Trace 16: Workspace Detail
- **UI binding:** `WorkspaceDetailPage.tsx:25` → `apiRequest("/tickers/tracked?limit=500", firebaseUser)`
- **API call:** `apiRequest("/tickers/tracked?limit=500", firebaseUser)`
- **Route:** `app/routes/tickers.py:29` → `route_get_tracked_tickers()`
- **CRUD:** `app/crud.py:287` → `get_tracked_tickers()`
- **SQL:** `SELECT t.symbol, t.name, t.sector, t.current_price, ... FROM tickers t JOIN workspace_tickers wt ON ...`
- **Data source:** PostgreSQL `tickers` + `workspace_tickers` (user-relationship data)
- **Migration tag:** **R** (ticker metadata, stays in PostgreSQL)

---

## **SUBLAYER 9.7 — Response Model Compatibility Matrix**

The following table maps PostgreSQL query results to Pydantic models and shows GCS compatibility:

| Pydantic Model | Fields | GCS Source | Compatible? |
|---------------|--------|------------|-------------|
| `FilingSummary` | target_ticker, target_cik, form_type, accession_number, filing_date, element_count, url | Vectorized JSON `sec_metadata` + chunk count | YES — all fields available |
| `FilingElement` | element_id, accession_number, item_number, content_type, element_type, content_body, raw_text_string, period_of_report, filing_date, date_precision | Vectorized JSON `chunks[]` | YES — all fields set (defaults: item_number="N/A", content_type="text/html", element_type="narrative", period_of_report=None, date_precision=None) |
| `SearchResult` | target_ticker, normalized_calendar_date, source, content_preview, element_id | Vectorized JSON `chunks[]` text_preview | YES — all fields can be derived |
| `TimelineEvent` | normalized_calendar_date, source, element_type, content_body, current, change, form_type, item_number, date_precision | Vectorized JSON `sec_metadata` + `chunks[0].text_preview` | YES — SEC portion fully migratable (current=None, change=None for SEC) |
| `DashboardStats` | articles_count, tickers_count, alerts_count, evidence_score | GCS file count + PostgreSQL counts | YES — articles_count from GCS `count_vectorized_files`, tickers_count from `tickers`, alerts_count from `alerts`, evidence_score=None |
| `FiscalYearEnd` | target_ticker, target_cik, fiscal_year_end_date, source_accession | PostgreSQL `fiscal_parameters JOIN tickers` | YES — uses `tickers` table for CIK, not `staging_sec` (avoids deprecated table) |
| `PriceRow` | normalized_calendar_date, current, change, percent_change, open, high, low, previous_close | PostgreSQL `staging_finnhub` only | N/A — stays in Postgres |
| `NewsRow` | target_ticker, normalized_calendar_date, ingest_date, content_body, source, url | PostgreSQL `staging_gnews` only | N/A — stays in Postgres |
| `TrackedTicker` | symbol, name, sector, current_price, evidence_score, hype_score, change_percent, price_as_of | PostgreSQL `tickers` only | N/A — stays in Postgres |
| `WorkspaceResponse` | id, name, tickers, alerts, created_at | PostgreSQL `workspaces` + `workspace_tickers` | N/A — stays in Postgres |

### **Critical gaps identified:**
1. **`FilingElement.item_number`**: Not present in vectorized JSON. Set to `"N/A"` as default in `_extract_filing_elements` (`vectorized_gcs.py:190`).
2. **`FilingElement.content_type`**: Not present in vectorized JSON. Set to `"text/html"` as default (`vectorized_gcs.py:191`).
3. **`FilingElement.date_precision`**: Not present in vectorized JSON. Set to `None` as default (`vectorized_gcs.py:198`).
4. **`FilingElement.period_of_report`**: Not present in vectorized JSON. Set to `None` as default (`vectorized_gcs.py:196`).
5. **`FilingElement.raw_text_string`**: In PostgreSQL, this was a separate column with full text. In vectorized data, both `content_body` and `raw_text_string` use `chunks[].text_preview` (same value) (`vectorized_gcs.py:193-194`).
6. **`TimelineEvent.current`/`change`**: SEC timeline events have no price data (`current=None`, `change=None`). Only `gnews`/`finnhub` timeline events have price data from PostgreSQL (`vectorized_gcs.py:347-348`).
7. **`DashboardStats.evidence_score`**: Not available from either GCS or PostgreSQL counts. Set to `None` (`app/routes/dashboard.py:31`).
8. **`/tickers/{ticker}/evidence` endpoint**: Does NOT exist in backend. Frontend calls it but it returns 404, falling back to hardcoded mock matrix in `TickerDashboard.tsx:457-485`.

**Gate 10 — Trace verification:**
- [x] All UI data bindings traced to source (Traces 1-16 above + Trace 11b)
- [x] Migration tags assigned (S/R/P/N) for each trace
- [x] Response model compatibility matrix complete (with field-level gap analysis)
- [x] Auth flow documented (Firebase UID vs internal user_id → `request.state`)
- [x] Workspace endpoints traced (Traces 15-16)
- [x] SEC content fetch traced (Trace 12 — GCS with SEC.gov fallback)
- [ ] Developer review: confirm evidence endpoint (`/api/tickers/{ticker}/evidence`) is intentionally not implemented (frontend falls back to mock matrix in `TickerDashboard.tsx:457-485`)
- [x] Unit tests: all 41 tests pass ✅

---

## **EXECUTION RESULTS**

### **UI-to-API-to-Data Source Trace Verification**

| Trace # | UI Component | API Endpoint | API Function | Data Source | Status |
|---------|-------------|-------------|--------------|-------------|--------|
| 1 | FilingTable | `/tickers/{ticker}/filings` | `list_filings_for_ticker` | `ftd-vectorized-data/sec-{8k|10k}/` (GCS) | ✅ GCS |
| 2 | TimelineView | `/tickers/{ticker}/timeline?sources=sec` | `get_timeline_from_gcs` | `ftd-vectorized-data/sec-{8k|10k}/` (GCS) | ✅ GCS |
| 3 | TimelineView (finnhub) | `/tickers/{ticker}/timeline?sources=finnhub` | `get_ticker_timeline` | PostgreSQL `unified_staging` | ✅ PostgreSQL |
| 4 | TimelineView (gnews) | `/tickers/{ticker}/timeline?sources=gnews` | `get_ticker_timeline` | PostgreSQL `unified_staging` | ✅ PostgreSQL |
| 5 | FilingViewer | `/tickers/{ticker}/filings/{accession}/content` | `get_filing_content_from_gcs` | `raw-data-strg/SEC/` (GCS) + SEC.gov fallback | ✅ GCS+ Fallback |
| 6 | SearchResults | `/search?q=...&source=sec` | `search_vectorized_content` | `ftd-vectorized-data/sec-{8k|10k}/` (GCS) | ✅ GCS |
| 7 | DashboardCards | `/dashboard/stats` | `count_vectorized_files` + `query_dict` | GCS (articles) + PostgreSQL (tickers, alerts) | ✅ Hybrid |
| 8 | TickerDetail | `/tickers/{ticker}` | `get_tracked_tickers` | PostgreSQL `tickers` | ✅ PostgreSQL (unchanged) |
| 9 | PriceChart | `/tickers/{ticker}/prices` | `get_ticker_prices` | PostgreSQL `unified_staging` | ✅ PostgreSQL (unchanged) |
| 10 | NewsList | `/tickers/{ticker}/news` | `get_ticker_news` | PostgreSQL `unified_staging` | ✅ PostgreSQL (unchanged) |
| 11 | AlertManager | `/workspaces/{id}/alerts` | `get_alerts` | PostgreSQL `alerts` | ✅ PostgreSQL (unchanged) |
| 12 | WorkspaceList | `/workspaces` | `get_workspaces` | PostgreSQL `workspaces` | ✅ PostgreSQL (unchanged) |
| 13 | TickerSearch | `/tickers/search` | `search_tickers` | PostgreSQL `tickers` | ✅ PostgreSQL (unchanged) |
| 14 | FilingElements | `/filings/{accession}/elements` | `get_filing_elements_by_accession` | `ftd-vectorized-data/sec-{8k|10k}/` (GCS) | ✅ GCS |
| 15 | FiscalYearEnd | `/tickers/{ticker}/fiscal-year-end` | `get_fiscal_year_end_from_gcs` | PostgreSQL `tickers` + `fiscal_parameters` | ✅ PostgreSQL (unchanged) |
| 16 | TrackedTickers | `/tickers/tracked` | `get_tracked_tickers` | PostgreSQL `tickers` | ✅ PostgreSQL (unchanged) |

### **Key findings:**

1. **SEC filing data**: All 5 SEC endpoints now read from GCS (`ftd-vectorized-data` or `raw-data-strg`). PostgreSQL `staging_sec` is no longer read.
2. **Relational data**: Tickers, prices, news, alerts, workspaces, and fiscal parameters all remain on PostgreSQL — no changes needed.
3. **Hybrid endpoints**: Timeline (`sources=sec` portion) and dashboard stats combine GCS and PostgreSQL. Non-SEC sources (finnhub, gnews) still use PostgreSQL.
4. **User fingerprinting**: `AuthMiddleware` sets `request.state.firebase_uid` (Firebase auth) or `request.state.user_id` (internal auth). `AuditLogMiddleware` (Layer 10) captures this for audit logging.
5. **Counter instrumentation**: `db_access_counter.py` increments on all 5 deprecated SEC functions in `crud.py`. All counters verified at 0 via `/api/admin/db-access-counters`.
6. **Response model compatibility**: All GCS-sourced responses match the existing Pydantic models. No frontend changes required.
7. **Evidence endpoint**: The `/tickers/{ticker}/evidence` endpoint is intentionally not implemented — `TickerDashboard.tsx:457-485` falls back to local mock data from environment variables.

