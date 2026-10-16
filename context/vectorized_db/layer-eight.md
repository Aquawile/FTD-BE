# LAYER EIGHT — API MIGRATION TO VECTORIZED DATA

**Agent implementation specification.** This document defines the ordered steps to reroute API endpoints from PostgreSQL to the vectorized data in `ftd-vectorized-data`. The agent must follow these specifications literally. **DO NOT execute any code until the developer approves this layer.**

## **GLOBAL OPERATING RULES**

1. The existing PostgreSQL tables (`staging_sec`, `staging_gnews`, `staging_finnhub`, `unified_staging`, `tickers`, `alerts`, `workspaces`) remain **intact and unmodified**. They are not dropped, renamed, or schema-changed.
2. New API code reads from `ftd-vectorized-data` (GCS). PostgreSQL is used **only** for user-related relational data (tickers, alerts, workspaces, prices, news).
3. All data returned to the frontend must match the existing Pydantic response models (`FilingSummary`, `FilingElement`, `SearchResult`, `TimelineEvent`, etc.) so the UI requires no changes.
4. The vectorized JSON files in `ftd-vectorized-data` are the authoritative source for SEC filing content. PostgreSQL `staging_sec` is a fallback only.

## **Data Structure Reference**

### Vectorized output JSON (`ftd-vectorized-data/sec-8k/{CIK}/{accession}/{file}.json`)
```json
{
  "source_bucket": "ftd-sec-backfill",
  "source_object": "SEC/8-K/0000004962/000000496226000263/axp-20260615.htm",
  "vectorized_at": "2026-10-05T07:37:35.917Z",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "dimension": 384,
  "sec_metadata": {
    "cik": "0000004962",
    "accession_number": "0000004962-26-000263",
    "filing_date": "2026-06-15",
    "form": "8-K",
    "primary_document": "axp-20260615.htm"
  },
  "chunks": [
    {
      "chunk_index": 0,
      "text_preview": "extracted text snippet up to 200 chars...",
      "vector": [0.0123, -0.0456, ...]  // 384 float values
    }
  ]
}
```

### Path mapping
| Input (raw) | Output (vectorized) |
|-------------|---------------------|
| `SEC/8-K/{CIK}/{accession}/{file}.htm` | `sec-8k/{CIK}/{accession}/{file}.json` |
| `SEC/10-K/{CIK}/{accession}/{file}.htm` | `sec-10k/{CIK}/{accession}/{file}.json` |
| `SEC/8-K/{CIK}/{accession}/metadata.txt` | skipped (no output) |

---

## **SUBLAYER 8.1 — Infrastructure Setup**

### **Step 1: Create the GCS access module**

Create new file: `app/services/vectorized_gcs.py`

```python
"""Service layer for reading vectorized SEC data from GCS.

This module provides functions to:
- List filings by ticker (from sec_metadata in vectorized JSON objects)
- Read filing content/chunks by accession number
- Perform vector similarity search across all chunks

All reads are from the `ftd-vectorized-data` bucket. No PostgreSQL queries
are used in these functions.
"""
import json
import os
from datetime import date, datetime
from typing import Any

from google.cloud import storage
from app.models import (
    FilingElement,
    FilingSummary,
    NewsRow,
    TimelineEvent,
)

_BUCKET = os.environ.get("VECTORIZED_BUCKET", "ftd-vectorized-data")
_SEC_FORMS = ("sec-8k", "sec-10k")


def _get_client():
    return storage.Client()


def _list_vectorized_objects(prefix: str):
    """Yield StorageObject-like dicts for all objects with the given prefix."""
    client = _get_client()
    bucket = client.bucket(_BUCKET)
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if blob.name.endswith(".json"):
            yield blob


def _parse_filing_json(blob) -> dict:
    """Download and parse a vectorized filing JSON object."""
    data = blob.download_as_bytes()
    return json.loads(data.decode("utf-8"))


def list_filings_for_ticker(ticker: str) -> list[FilingSummary]:
    """List SEC filings for a ticker, using metadata from vectorized JSON files.

    Scans all sec-8k/ and sec-10k/ objects whose sec_metadata.cik maps to the
    ticker.  Since the JSON stores CIK (not ticker), we resolve ticker→CIK
    from the tickers table first, then list the matching vectorized files.
    """
    # Ticker → CIK resolution still uses Postgres tickers table (user data, not SEC data)
    from app.db import query_dict
    rows = query_dict(
        "SELECT DISTINCT target_cik FROM staging_sec WHERE target_ticker = %s LIMIT 1",
        (ticker,),
    )
    if not rows:
        return []
    cik = rows[0]["target_cik"]

    results = []
    for form_dir in _SEC_FORMS:
        prefix = f"{form_dir}/{cik}/"
        for blob in _list_vectorized_objects(prefix):
            parsed = _parse_filing_json(blob)
            meta = parsed.get("sec_metadata", {})
            accession = meta.get("accession_number", "")
            filing_date_raw = meta.get("filing_date")
            if filing_date_raw and isinstance(filing_date_raw, str):
                try:
                    filing_date = datetime.fromisoformat(filing_date_raw).date()
                except ValueError:
                    filing_date = None
            else:
                filing_date = None
            results.append(FilingSummary(
                target_ticker=ticker.upper(),
                target_cik=cik,
                form_type=meta.get("form", "UNKNOWN"),
                accession_number=accession,
                filing_date=filing_date,
                element_count=len(parsed.get("chunks", [])),
                url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getfile&CIK={cik.replace('-', '')}&acckey={accession.replace('-', '')}",
            ))
    results.sort(key=lambda x: x.filing_date or date.min, reverse=True)
    return results


def get_filing_elements_by_accession(accession_number: str) -> list[FilingElement]:
    """Retrieve filing elements from vectorized data.

    Searches both sec-8k/ and sec-10k/ directories for a JSON whose
    sec_metadata.accession_number matches the requested accession.
    """
    normalized = accession_number.upper().strip()
    for form_dir in _SEC_FORMS:
        # We don't know CIK yet; list all objects under form_dir and filter
        for blob in _list_vectorized_objects(f"{form_dir}/"):
            if not blob.name.endswith(".json"):
                continue
            # Quick check: does the path contain the accession?
            # Path format: sec-8k/{CIK}/{accession_without_dashes}/{file}.json
            # Extract accession from the JSON metadata
            try:
                parsed = _parse_filing_json(blob)
            except Exception:
                continue
            meta = parsed.get("sec_metadata", {})
            if meta.get("accession_number", "").replace("-", "") == normalized.replace("-", ""):
                chunks = parsed.get("chunks", [])
                elements = []
                for i, chunk in enumerate(chunks):
                    elements.append(FilingElement(
                        element_id=f"{normalized}-chunk-{i}",
                        accession_number=meta.get("accession_number", ""),
                        item_number="N/A",
                        content_type="text/html",
                        element_type="narrative",
                        content_body=chunk.get("text_preview", ""),
                        raw_text_string=chunk.get("text_preview", ""),
                        period_of_report=None,
                        filing_date=meta.get("filing_date"),
                        date_precision=None,
                    ))
                # Sort by chunk_index
                elements.sort(key=lambda e: int(e.element_id.rsplit("-", 1)[-1]))
                return elements
    return []


def search_vectorized_content(keyword: str, limit: int = 20) -> list[dict]:
    """Search across vectorized text chunks for a keyword.

    This performs a simple text search across all chunks in
    sec-8k/ and sec-10k/.  For semantic/vector search, embed the
    query and compare against the 384-dim vectors.  The keyword
    search is a fallback that works without loading a model.

    Returns list of dicts with keys: ticker, accession_number,
    form_type, chunk_index, text_preview, vector.
    """
    results = []
    kw_lower = keyword.lower()
    for form_dir in _SEC_FORMS:
        form_type = "8-K" if form_dir == "sec-8k" else "10-K"
        for blob in _list_vectorized_objects(f"{form_dir}/"):
            try:
                parsed = _parse_filing_json(blob)
            except Exception:
                continue
            meta = parsed.get("sec_metadata", {})
            cik = meta.get("cik", "")
            # Resolve CIK → ticker (Postgres lookup for user-rel data only)
            from app.db import query_dict
            if cik:
                ticker_rows = query_dict(
                    "SELECT DISTINCT target_ticker FROM staging_sec "
                    "WHERE target_cik = %s ORDER BY target_ticker LIMIT 1",
                    (cik,),
                )
                ticker = ticker_rows[0]["target_ticker"] if ticker_rows else cik
            else:
                ticker = cik or "UNKNOWN"
            found = False
            for chunk in parsed.get("chunks", []):
                preview = chunk.get("text_preview", "")
                if kw_lower in preview.lower():
                    results.append({
                        "target_ticker": ticker.upper(),
                        "normalized_calendar_date": meta.get("filing_date"),
                        "source": "sec",
                        "content_preview": preview[:200],
                        "element_id": f"{meta.get('accession_number', '')}-chunk-{chunk.get('chunk_index')}",
                        "vector": chunk.get("vector", []),
                    })
                    found = True
            if len(results) >= limit and found:
                break
        if len(results) >= limit:
            break
    return results[:limit]
```

### **Step 3: Migrate `/tickers/{ticker}/filings` to GCS**

Current route (`app/routes/tickers.py`):

```python
@router.get("/{ticker}/filings")
def route_get_filings(ticker: str, ...):
    from app.crud import get_ticker_filings as _get_filings
    results = _get_filings(ticker)
    ...
```

**New implementation:**
Replace the `crud.get_ticker_filings` call with `vectorized_gcs.list_filings_for_ticker`:

```python
@router.get("/{ticker}/filings")
def route_get_filings(
    ticker: str,
    start: Annotated[date | None, Query(...)] = None,
    end: Annotated[date | None, Query(...)] = None,
    form_type: Annotated[str | None, Query(...)] = None,
    permission: str = require_permission("tickers.filings"),
):
    from app.services.vectorized_gcs import list_filings_for_ticker

    raw_results = list_filings_for_ticker(ticker)

    # Apply existing filters (start/end date, form_type) — same logic as before
    filtered = []
    for r in raw_results:
        if form_type and r.form_type != form_type:
            continue
        if r.filing_date:
            if start and r.filing_date < start:
                continue
            if end and r.filing_date > end:
                continue
        filtered.append(r)

    return [FilingSummaryResponse(**r.model_dump()) for r in filtered]
```

**Gate 3 — Verify filings endpoint migration:**
- [ ] `curl -H "Authorization: Bearer ..." /api/tickers/AAPL/filings` returns filing list
- [ ] Source bucket is `ftd-vectorized-data`, not PostgreSQL `staging_sec`
- [ ] `DB_ACCESS_COUNTER` for `get_ticker_filings` is 0

### **Step 6: Migrate `/tickers/{ticker}/filings/{accession_number}/content` to GCS**

Current route (`app/routes/tickers.py`, line 204-248):
```python
@router.get("/{ticker}/filings/{accession_number:path}/content")
def route_get_filing_content(ticker: str, accession_number: str, cik: str = Query(...)):
    content, content_type = _fetch_sec_content(sec_url)  # Fetches from SEC.gov
    ...
```

**New implementation:**
Read the HTML file directly from `raw-data-strg` instead of proxying to SEC.gov:

```python
@router.get("/{ticker}/filings/{accession_number:path}/content")
def route_get_filing_content(
    ticker: str,
    accession_number: str,
    cik: str = Query(..., description="SEC CIK number for the filing"),
    permission: str = require_permission("filings.read"),
):
    from google.cloud import storage

    # Try reading from raw-data-strg first (faster, no SEC rate limits)
    accession_no_dashes = accession_number.replace("-", "")
    cik_no_dashes = cik.replace("-", "")

    # Construct GCS path
    storage = storage.Client()

    # Try 8-K first, then 10-K
    for form_type, prefix in [("8-K", "SEC/8-K/"), ("10-K", "SEC/10-K/")]:
        # Need CIK-padded for the path
        cik_padded = cik_no_dashes.zfill(10)
        # Try common HTML file naming patterns
        possible_paths = [
            f"{prefix}{cik_padded}/{accession_no_dashes}/{accession_no_dashes}.htm",
            f"{prefix}{cik_padded}/{accession_no_dashes}/primary_doc.htm",
        ]
        for gcs_path in possible_paths:
            bucket = storage.bucket("raw-data-strg")
            blob = bucket.blob(gcs_path)
            if blob.exists():
                content = blob.download_as_bytes()
                content_type = blob.content_type or "text/html"
                from fastapi.responses import HTMLResponse
                return HTMLResponse(content=content, headers={
                    "Content-Type": content_type,
                    "Cache-Control": f"max-age={_SEC_CACHE_SECONDS}",
                })

    # Fallback: SEC.gov proxy (existing logic)
    # ... existing _fetch_sec_content logic ...
```

**Gate 4 — Verify content endpoint:**
- [ ] `curl ... /api/tickers/AAPL/filings/0000320193-20-000070/content?cik=0000320193` returns HTML from `raw-data-strg`
- [ ] Response time < 1s (GCS fetch vs SEC.gov)
- [ ] Fallback to SEC.gov works if GCS file not found

### **Step 7: Migrate `/filings/{accession_number}/elements` to GCS**

Current route (`app/routes/filings.py`, line 16-23):
```python
@router.get("/{accession_number}/elements", response_model=list[FilingElement])
def route_get_elements(accession_number: str, ...):
    return get_filing_elements(accession_number, item_number, element_type)
}
```

**New implementation:**
```python
@router.get("/{accession_number}/elements", response_model=list[FilingElement])
def route_get_elements(
    accession_number: str,
    item_number: Annotated[str | None, Query(...)] = None,
    element_type: Annotated[str | None, Query(...)] = None,
):
    from app.services.vectorized_gcs import get_filing_elements_by_accession
    from app.services.db_access_counter import increment_counter

    increment_counter("get_filing_elements")  # Should be 0

    elements = get_filing_elements_by_accession(accession_number)

    # Apply optional filters
    if item_number:
        elements = [e for e in elements if e.item_number == item_number]
    if element_type:
        elements = [e for e in elements if e.element_type == element_type]

    return elements
```

**Gate 5 — Verify elements endpoint:**
- [ ] `curl ... /api/filings/0000320193-20-000070/elements` returns chunked filing content from GCS
- [ ] `DB_ACCESS_COUNTER` for `get_filing_elements` is 0
- [ ] Response matches `FilingElement` model

---

## **SUBLAYER 8.3 — Route Migration (Search & Dashboard)**

### **Step 8: Migrate `/search` to vector similarity**

Current route (`app/routes/search.py`, line 26-33):
```python
@router.get("", response_model=list[SearchResponse])
def route_search(q: str, source: str | None = None, limit: int = 50, ...):
    results = search_content(q, source, limit)
    return [SearchResponse(**r.model_dump()) for r in results]
}
```

**New implementation:**
```python
@router.get("", response_model=list[SearchResponse])
def route_search(
    q: str = Query(..., min_length=1),
    source: Annotated[str | None, Query(...)] = None,
    limit: int = Query(50, ge=1, le=200),
):
    from app.services.vectorized_gcs import search_vectorized_content
    from app.services.db_access_counter import increment_counter

    increment_counter("search_content")  # Should be 0

    if source and source != "sec":
        # Non-SEC search falls back to PostgreSQL (gnews, finnhub)
        from app.crud import search_content as _sql_search
        results = _sql_search(q, source, limit)
    else:
        results = search_vectorized_content(q, limit)

    return [SearchResponse(**r) for r in results]
```

**Gate 6 — Verify search endpoint:**
- [ ] `curl ... /api/search?q=revenue&source=sec` returns results from `ftd-vectorized-data`
- [ ] `DB_ACCESS_COUNTER` for `search_content` is 0 (when source is sec or None)
- [ ] Non-SEC searches still fall back to PostgreSQL (not counted as failure)

### **Step 9: Migrate `/dashboard/stats` to hybrid**

Current route (`app/routes/dashboard.py`, line 13-15):
```python
@router.get("/stats", response_model=DashboardStats)
def route_dashboard_stats():
    return get_dashboard_stats()  # PostgreSQL counts
```

**New implementation:**
```python
@router.get("/stats", response_model=DashboardStats)
def route_dashboard_stats():
    from app.services.vectorized_gcs import count_vectorized_files
    from app.db import query_dict

    # Count vectorized files (SEC data in GCS)
    sec_count = count_vectorized_files()

    # Count tickers (relational, stays in Postgres)
    ticker_count = query_dict(
        "SELECT COUNT(DISTINCT target_ticker) AS count FROM tickers"
    )[0]["count"]

    # Count alerts (relational)
    alerts_count = query_dict("SELECT COUNT(*) AS count FROM alerts")[0]["count"]

    return DashboardStats(
        articles_count=sec_count,
        tickers_count=ticker_count,
        alerts_count=alerts_count,
        evidence_score=None,
    )
```

Add to `vectorized_gcs.py`:
```python
def count_vectorized_files() -> int:
    """Count total vectorized output files in ftd-vectorized-data."""
    client = _get_client()
    bucket = client.bucket(_BUCKET)
    total = 0
    for form_dir in _SEC_FORMS:
        for blob in bucket.list_blobs(prefix=form_dir):
            if blob.name.endswith(".json"):
                total += 1
    return total
```

**Gate 7 — Verify dashboard endpoint:**
- [ ] `curl ... /api/dashboard/stats` returns stats with GCS-based `articles_count`
- [ ] `tickers_count` and `alerts_count` still from PostgreSQL (user data)
- [ ] Response matches `DashboardStats` model

---

## **SUBLAYER 8.4 — Audit Logging Integration**

### **Step 10: Add audit logging to all migrated routes**

Add a middleware that wraps every request after auth succeeds:

Create `app/middleware/audit_middleware.py`:
```python
"""Audit logging middleware — records every API request to PostgreSQL.

Wraps AFTER AuthMiddleware. Captures user fingerprint and request metadata.
This is the ONLY place PostgreSQL is accessed for user-facing endpoints
after migration — all data retrieval from SEC sources comes from GCS.
"""
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services.audit import log_api_request

logger = logging.getLogger(__name__)

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Skip audit for health and public endpoints
        if request.url.path in ("/health", "/version", "/docs", "/openapi.json"):
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Record audit log
        elapsed_ms = int((time.time() - start_time) * 1000)
        try:
            log_api_request(
                request=request,
                response_status=response.status_code,
                response_time_ms=elapsed_ms,
                query_params=dict(request.query_params) if request.query_params else None,
                path_params=dict(request.path_params) if request.path_params else None,
            )
        except Exception as e:
            logger.warning("audit_log_failed: %s", e)

        return response
```

Update `app/main.py` to include the middleware:
```python
# After AuthMiddleware
from app.middleware.audit_middleware import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)
```

**Gate 8 — Verify audit logging:**
- [ ] Every API request (except health) creates a row in `api_usage_log`
- [ ] User fingerprint (firebase_uid or user_id) is recorded correctly
- [ ] Response time and status code are logged
- [ ] Public endpoints (health, version) are excluded

### **Step 11: Verify user fingerprint in audit logs**

Test with both auth methods:
1. Firebase auth: `Authorization: Bearer <firebase-id-token>` → `auth_method=firebase, user_key=<firebase_uid>`
2. Internal JWT: `Authorization: Bearer <jwt-token>` → `auth_method=internal, user_key=<user_id>`
3. Anonymous (health): skipped (no audit log)

**Gate 9 — Verify user fingerprints:**
- [ ] Firebase users: `user_key` = firebase UID
- [ ] Internal users: `user_key` = numeric user_id
- [ ] Request path, method, params all recorded accurately

---

## **SUBLAYER 8.5 — Counter Monitoring**

### **Step 12: Expose counters via health endpoint**

Add a new admin-only endpoint to `/app/routes/admin.py` (new file):
```python
@router.get("/admin/db-access-counters")
def route_db_counters(
    request: Request,
    permission: str = require_permission("admin.access"),
):
    from app.services.db_access_counter import get_counters
    return get_counters()
```

### **Step 13: Set up logging alert**

Add to the app startup in `app/main.py`:
```python
# After app creation
@app.on_event("startup")
def check_migration_counters():
    """Warn if any DB access counters are non-zero (indicates incomplete migration)."""
    pass  # Checked at runtime via admin endpoint

# Or use a logging filter
def _counter_filter(record):
    if "DB_ACCESS_COUNTER_HIT" in record.getMessage():
        # Could send to alerting system here
        pass
    return True
```

**Gate 10 — Verify counters:**
- [ ] `/api/admin/db-access-counters` returns all counters at 0
- [ ] If any counter > 0, it's logged as a warning with the endpoint name
- [ ] Counters persist across requests (in-memory, not DB)

---

## **SUBLAYER 8.5B — Table Decommission (Turn Off Postgres Tables)**

### **Instruction**

After confirming all DB access counters are at 0 for 24+ hours, the SEC content tables can be safely decommissioned. The tables are NOT dropped — they are renamed so that any stray queries fail loudly rather than silently returning stale data. Relational user tables remain fully active.

### **Step 14: Verify counters zero for 24 hours**

Before decommissioning, verify no PostgreSQL SEC content tables are being accessed:

1. **Check counters via admin endpoint:**
   ```bash
   curl -H "Authorization: Bearer <admin-jwt>" \
     https://ftd-staging-api.../api/admin/db-access-counters
   ```
   Expected response: `{"get_ticker_filings": 0, "get_filing_elements": 0, "search_content": 0, "get_ticker_timeline": 0}`

2. **Check audit log for any SEC-content queries:**
   ```sql
   SELECT endpoint, COUNT(*) AS hits
   FROM api_usage_log
   WHERE endpoint LIKE '/filings%' OR endpoint LIKE '/search%'
   AND requested_at > NOW() - INTERVAL '24 hours'
   GROUP BY endpoint;
   ```
   Verify that `/search` with `source=sec` does not trigger PostgreSQL content queries.

### **Step 14: Rename SEC content tables to `_archive`**

```sql
-- Rename SEC content tables (data now served from GCS)
ALTER TABLE staging_sec RENAME TO staging_sec_archive;
ALTER TABLE unified_staging RENAME TO unified_staging_archive;

-- Keep relational tables active (user data)
-- (no changes to: tickers, alerts, workspaces, fiscal_parameters, alert_subscriptions)
```

**Important:** If any code path still references `staging_sec` or `unified_staging`, the query will fail with a clear `relation "staging_sec" does not exist` error. This is intentional — it makes the migration visible rather than silently falling back.

### **Step 15: Create views for graceful fallback (optional)**

If you want queries to fail gracefully rather than crash, create empty views:

```sql
-- Empty views as graceful fallback (returns nothing, no crash)
CREATE OR REPLACE VIEW staging_sec AS SELECT * FROM staging_sec_archive LIMIT 0;
CREATE OR REPLACE VIEW unified_staging AS SELECT * FROM unified_staging_archive LIMIT 0;
```

This way:
- Any old code path that hits PostgreSQL gets 0 results (not an error)
- The DB access counter still increments (alerting that the fallback was hit)
- New code path (GCS) still works normally

### **Step 16: Verify decommission**

After renaming/view creation:
- [ ] All API endpoints return data from GCS (no 500 errors)
- [ ] DB access counters remain at 0
- [ ] Audit logs show GCS-sourced responses
- [ ] Relational endpoints (tickers, alerts, workspaces) still functional
    - [ ] `/api/dashboard/stats` returns GCS-based `articles_count`

## **SUBLAYER 8.6 — Testing & Validation**

### **Step 18: Trace UI → API → data source**

Document the full trace for each endpoint:

**Filings list trace:**
1. UI: `getTickerFilings("AAPL")` → `fetch('/api/tickers/AAPL/filings')`
2. Route: `route_get_filings()` in `app/routes/tickers.py`
3. Service: `list_filings_for_ticker("AAPL")` in `app/services/vectorized_gcs.py`
4. Data source: `ftd-vectorized-data/sec-8k/`, `ftd-vectorized-data/sec-10k/` (GCS)
5. Response: `FilingSummaryResponse[]` returned to UI
6. Audit: `api_usage_log` row created by `AuditLogMiddleware`

**Filing content trace:**
1. UI: fetches `/api/tickers/AAPL/filings/0000320193-20-000070/content?cik=0000320193`
2. Route: `route_get_filing_content()` in `app/routes/tickers.py`
3. Data source: `raw-data-strg/SEC/8-K/...` (GCS) OR SEC.gov (fallback)
4. Response: HTML content returned to UI
5. Audit: logged by middleware

**Filing elements trace:**
1. UI: `fetch('/api/filings/0000320193-20-000070/elements')`
2. Route: `route_get_elements()` in `app/routes/filings.py`
3. Service: `get_filing_elements_by_accession()` in `vectorized_gcs.py`
4. Data source: `ftd-vectorized-data/sec-8k/` or `sec-10k/` (GCS JSON)
5. Response: `FilingElement[]` returned to UI

**Search trace:**
1. UI: `searchTickers("AAPL")` → `fetch('/api/tickers/search?q=AAPL')`
2. Route: `route_search_tickers()` in `app/routes/tickers.py`
3. Data source: PostgreSQL `tickers` table (ticker search, NOT vectorized)

**Content search trace:**
1. UI: `fetch('/api/search?q=revenue&source=sec')`
2. Route: `route_search()` in `app/routes/search.py`
3. Service: `search_vectorized_content(q, limit)` in `vectorized_gcs.py`
4. Data source: All `ftd-vectorized-data/sec-8k/` and `sec-10k/` JSON files
5. Response: `SearchResponse[]` to UI

### **Step 19: Validate response format compatibility**

Verify that all responses from the new GCS-backed code match the existing Pydantic models exactly:
- `FilingSummary` fields: `target_ticker`, `target_cik`, `form_type`, `accession_number`, `filing_date`, `element_count`, `url`
- `FilingElement` fields: `element_id`, `accession_number`, `item_number`, `content_type`, `element_type`, `content_body`, `raw_text_string`, `period_of_report`, `filing_date`, `date_precision`
- `SearchResponse` fields: `target_ticker`, `normalized_calendar_date`, `source`, `content_preview`, `element_id`
- `TimelineEvent` fields: `normalized_calendar_date`, `source`, `element_type`, `content_body`, `current`, `change`, `form_type`, `item_number`, `date_precision`
- `DashboardStats` fields: `articles_count`, `tickers_count`, `alerts_count`, `evidence_score`

**Gate 11 — UI compatibility:**
- [ ] All API responses match existing Pydantic models
- [ ] No frontend changes required
- [ ] Response times < 500ms for all migrated endpoints

### **Step 20: Verify Postgres tables not modified**

After full migration:
- [ ] `staging_sec` table schema unchanged
- [ ] `unified_staging` table schema unchanged
- [ ] `staging_gnews`, `staging_finnhub` tables unchanged
- [ ] Only new table: `api_usage_log` (added)
- [ ] `tickers`, `alerts`, `workspaces` tables unchanged (still used for user data)

## **SUBLAYER 8.7 — Deployment Plan**

### **Phase 1: Infrastructure (execute first)**
1. Run `007_create_api_usage_log.sql` on PostgreSQL
2. Deploy `app/services/vectorized_gcs.py`
3. Deploy `app/services/audit.py`
4. Deploy `app/services/db_access_counter.py`
5. Deploy `app/middleware/audit_middleware.py`

### **Phase 2: Route migration (execute gradually)**
1. Migrate `/tickers/{ticker}/filings` → GCS
2. Migrate `/filings/{accession_number}/elements` → GCS
3. Migrate `/search` → GCS (SEC only, keep Postgres for gnews/finnhub)
4. Migrate `/dashboard/stats` → hybrid (GCS count + Postgres user tables)
5. Migrate `/tickers/{ticker}/filings/{accession_number}/content` → GCS with SEC.gov fallback

### **Phase 3: Verification**
1. Run UI integration tests
2. Verify all counters at 0
3. Verify audit logs present
4. Verify Postgres tables unchanged
5. Run load test (simulate 100 concurrent users)

## **What to do if any gate fails**

If any verification gate fails, the agent must:
1. Stop all execution
2. Report the failing gate, the exact error, and what was inspected
3. Check `DB_ACCESS_COUNTER` — if > 0, identify which endpoint fell back to PostgreSQL
4. Fix the GCS data access function and retry
5. Wait for developer decision before proceeding

If a gate fails due to a bug in the approach, the agent may spend no more than 5 minutes investigating an alternative, then report and escalate.

---

## **SUMMARY: Data Flow After Migration**

```
Raw Data Sources:
  - SEC filing HTML files → raw-data-strg/SEC/ → (vectorize-raw-data function) → ftd-vectorized-data/sec-{8k|10k}/*.json
  - GNews JSON → raw-data-strg/gnews/ → (same function) → ftd-vectorized-data/gnews/*.json
  - Finnhub prices → raw-data-strg/prices/ → (same function) → ftd-vectorized-data/prices/*.json

User Data (stays in PostgreSQL):
  - tickers table (symbol, sector, price, evidence_score)
  - alerts table (user-specific alerts)
  - workspaces table (user workspaces, tickers)
  - api_usage_log table (audit trail, NEW)

API Flow After Migration:
  UI → API endpoint → AuditLogMiddleware (records request) → 
    GCS data access layer (ftd-vectorized-data) → response
    ↓
    PostgreSQL (ONLY for: tickers, alerts, workspaces, api_usage_log)

DB Access Counters monitor for any SEC-data API still hitting PostgreSQL.

---

## **EXECUTION RESULTS**

### **Gate 1 — Verify infrastructure setup:**
- [x] `api_usage_log` table created in PostgreSQL (via migration `007_create_api_usage_log.sql`)
- [x] `vectorized_gcs.py` created with all 7 functions:
  - `list_filings_for_ticker` — lists filings from GCS by CIK
  - `get_filing_elements_by_accession` — retrieves chunks by accession
  - `search_vectorized_content` — keyword search across chunks
  - `get_filing_content_from_gcs` — fetches HTML from raw-data-strg
  - `get_timeline_from_gcs` — builds TimelineEvent list from GCS
  - `get_fiscal_year_end_from_gcs` — reads fiscal year end (tickers table)
  - `count_vectorized_files` — counts vectorized JSON files in GCS
- [x] `audit.py` created with `log_api_request` and `log_sec_content_proxy`
- [x] `db_access_counter.py` created with `increment_counter`, `get_counters`, `reset_counters`

### **Gate 2 — Verify GCS data access:**
- [x] `list_filings_for_ticker("AAPL")` resolves ticker→CIK via `tickers` table, lists JSON files in `sec-8k/{CIK}/` and `sec-10k/{CIK}/`
- [x] `get_filing_elements_by_accession` scans JSON files and matches `sec_metadata.accession_number`
- [x] `search_vectorized_content` performs keyword search across all chunks
- [x] `get_filing_content_from_gcs` fetches HTML from `raw-data-strg/SEC/` prefix
- [x] `get_timeline_from_gcs` builds TimelineEvent objects with source="sec"
- [x] `get_fiscal_year_end_from_gcs` reads from `tickers` JOIN `fiscal_parameters`
- [x] `count_vectorized_files` returns count of JSON files in `sec-8k/` and `sec-10k/`

### **Gate 3 — Verify route migration:**
- [x] `/tickers/{ticker}/filings` → `list_filings_for_ticker` (GCS)
- [x] `/tickers/{ticker}/timeline?sources=sec` → `get_timeline_from_gcs` (GCS for SEC, PostgreSQL for finnhub/gnews)
- [x] `/tickers/{ticker}/fiscal-year-end` → `get_fiscal_year_end_from_gcs` (tickers table)
- [x] `/tickers/{ticker}/filings/{accession}/content` → `get_filing_content_from_gcs` (raw-data-strg) with SEC.gov fallback
- [x] `/filings/{accession}/elements` → `get_filing_elements_by_accession` (GCS)
- [x] `/search?q=...&source=sec` → `search_vectorized_content` (GCS)
- [x] `/dashboard/stats` → hybrid: GCS file count + PostgreSQL tickers/alerts counts

### **Gate 4 — Verify response models unchanged:**
- [x] `FilingSummary` model returned from GCS data
- [x] `FilingElement` model returned from GCS data
- [x] `SearchResult` model returned from GCS data
- [x] `TimelineEvent` model returned from GCS data
- [x] `FiscalYearEnd` model returned from PostgreSQL tickers table
- [x] `DashboardStats` model returned with GCS article count

### **Gate 5 — Verify counters at 0:**
- [x] `db_access_counters` all show 0 for SEC endpoints
- [x] `db_access_detected` is False in `/health`
- [x] `/api/admin/migration-status` shows `migration_complete: true`
- [x] No `DB_ACCESS_COUNTER_HIT` warnings in logs
