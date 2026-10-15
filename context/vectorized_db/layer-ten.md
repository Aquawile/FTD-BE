# LAYER TEN — AUDIT LOGGING, USER FINGERPRINTING & LOG FILES

**Agent implementation specification.** This layer establishes dual-channel audit logging for all API requests: PostgreSQL `api_usage_log` table for structured audit data, and file-based JSON logs for SEC proxy access. User fingerprinting attributes each request to a unique identity. **DO NOT execute any code until the developer approves this layer.**

## **GLOBAL OPERATING RULES**

1. All audit logging is append-only. No existing data is modified or deleted.
2. The `api_usage_log` table is the ONLY new PostgreSQL table created (via migration `007_create_api_usage_log.sql`).
3. File-based audit logs are written to `/var/log/ftd-api/sec-content-proxy.log` on the GCE VM (not version-controlled).
4. User fingerprinting reads from `request.state.firebase_uid` (Firebase auth) or `request.state.user_id` (internal auth).
5. Anonymous requests (no auth) are logged to file only, NOT to PostgreSQL.
6. All logging is best-effort — a logging failure MUST NOT interrupt the API response.

## **Data Model: `api_usage_log` Table**

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `user_key` | TEXT | Firebase UID, user_id, or "anonymous" |
| `auth_method` | TEXT | "firebase", "internal", or "anonymous" |
| `endpoint` | TEXT | Request path (e.g., `/api/tickers/AAPL/filings`) |
| `http_method` | TEXT | HTTP method (GET, POST, etc.) |
| `query_params` | JSONB | Query string parameters |
| `path_params` | JSONB | Path parameters |
| `request_body` | JSONB | Request body (for POST/PUT) |
| `response_status` | INTEGER | HTTP status code |
| `response_time_ms` | INTEGER | Response time in milliseconds |
| `requested_at` | TIMESTAMP WITH TIME ZONE | When the request was received (default NOW()) |
| `created_at` | TIMESTAMP WITH TIME ZONE | Row creation time (default NOW()) |

## **SUBLAYER 10.1 — Infrastructure Setup**

### **Step 1: Create the audit logging utility**

Create new file: `app/services/audit.py`

```python
"""Audit logging utility — records API requests to PostgreSQL and file logs.

This module provides:
1. User fingerprint capture (firebase_uid or user_id) from request.state
2. INSERT into api_usage_log table for authenticated requests
3. Structured file logging for SEC proxy access (anonymous requests)
"""
import json
import logging
import time
from fastapi import Request

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")


def get_user_fingerprint(request: Request) -> tuple[str, str]:
    """Extract user fingerprint from request.state.

    Returns (user_key, auth_method) tuple.
    - user_key: firebase_uid or user_id string
    - auth_method: "firebase" or "internal"
    """
    firebase_uid = getattr(request.state, "firebase_uid", None)
    if firebase_uid:
        return firebase_uid, "firebase"
    user_id = getattr(request.state, "user_id", None)
    if user_id is not None:
        return str(user_id), "internal"
    return "anonymous", "anonymous"


def log_api_request(request: Request, response_status: int, response_time_ms: int,
                    query_params: dict | None = None,
                    path_params: dict | None = None,
                    request_body: dict | None = None) -> None:
    """Insert an API request record into the api_usage_log table.

    Only logs authenticated requests (non-anonymous).
    """
    from app.db import execute

    user_key, auth_method = get_user_fingerprint(request)
    if auth_method == "anonymous":
        return

    endpoint = str(request.url.path)
    method = request.method
    try:
        execute(
            """
            INSERT INTO api_usage_log
              (user_key, auth_method, endpoint, http_method,
               query_params, path_params, request_body,
               response_status, response_time_ms, requested_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                user_key, auth_method, endpoint, method,
                json.dumps(query_params) if query_params else None,
                json.dumps(path_params) if path_params else None,
                json.dumps(request_body) if request_body else None,
                response_status, response_time_ms,
            ),
        )
    except Exception as e:
        logger.warning("audit_log_write_failed: %s", e)


def log_sec_content_proxy(request: Request, endpoint: str, status: int,
                          duration_ms: int, details: dict) -> None:
    """Log SEC content proxy access to the audit file logger.

    Logs ALL requests (including anonymous) to file-based audit log.
    """
    user_key, auth_method = get_user_fingerprint(request)
    audit_logger.info(
        "sec_content_proxy",
        extra={
            "user_key": user_key,
            "method": "GET",
            "path": endpoint,
            "status": status,
            "duration_ms": duration_ms,
            "details": {
                "auth_method": auth_method,
                **details,
            },
        },
    )
```

### **Step 2: Create the logging configuration**

Create new file: `app/logging_config.py`

```python
"""Logging configuration for structured audit logging.

Configures:
1. Root logger — application logging (stdout, standard format)
2. Audit logger — SEC proxy access, structured JSON to file and stdout

File handler writes to /var/log/ftd-api/sec-content-proxy.log
(if directory does not exist, falls back to stdout-only).
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format audit log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "user_key"):
            entry["user_key"] = record.user_key
        if hasattr(record, "method"):
            entry["method"] = record.method
        if hasattr(record, "path"):
            entry["path"] = record.path
        if hasattr(record, "status"):
            entry["status"] = record.status
        if hasattr(record, "duration_ms"):
            entry["duration_ms"] = record.duration_ms
        if hasattr(record, "details"):
            entry["details"] = record.details
        return json.dumps(entry)


def setup_logging() -> None:
    """Configure root and audit loggers."""

    # Root logger — stdout, standard format
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    root_logger.addHandler(root_handler)

    # Audit logger — structured JSON to file and stdout
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    json_formatter = JSONFormatter()

    # File handler (best-effort)
    log_dir = "/var/log/ftd-api"
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "sec-content-proxy.log"))
        file_handler.setFormatter(json_formatter)
        audit_logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Fallback: stdout only if we can't write to file
        pass

    # Stdout handler for audit logger
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(json_formatter)
    audit_logger.addHandler(stdout_handler)
```

### **Step 3: Create the audit middleware**

Create new file: `app/middleware/audit_middleware.py`

```python
"""Audit logging middleware — wraps each request with audit logging.

Registered AFTER AuthMiddleware so request.state is populated with
user identity information.
"""
import time
import logging
from fastapi import Request, Response
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """Middleware that logs every API request to the audit trail."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        start_time = time.time()

        # Capture response status
        status_code = 200

        async def _log_response(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)

        async def _wrapped_send(message: dict) -> None:
            await _log_response(message)
            await send(message)

        await self.app(scope, receive, _wrapped_send)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Log to PostgreSQL (only for authenticated requests)
        from app.services.audit import log_api_request
        try:
            query_params = dict(request.query_params)
            path_params = scope.get("path_params", {})
            log_api_request(request, status_code, elapsed_ms,
                            query_params=query_params,
                            path_params=path_params)
        except Exception as e:
            logger.warning("audit_middleware_error: %s", e)
```

**Gate 1 — Verify middleware setup:**
- [ ] `app/services/audit.py` created with `log_api_request` and `log_sec_content_proxy`
- [ ] `app/services/user_fingerprint.py` created with `get_user_fingerprint`
- [ ] `app/logging_config.py` created with `setup_logging` and `JSONFormatter`
- [ ] `app/middleware/audit_middleware.py` created with `AuditLogMiddleware`
- [ ] `AuditLogMiddleware` registered in `app/main.py` after `AuthMiddleware`

---

## **SUBLAYER 10.2 — SEC Proxy Audit Logging**

### **Step 4: Instrument SEC content proxy endpoint with file logging**

In `app/routes/tickers.py`, the `route_get_filing_content` endpoint must log all SEC content proxy access to the file-based audit logger.

Add timing and audit logging to the `route_get_filing_content` function:
```python
import time as _time
_audit_start = _time.time()

# ... after GCS or SEC.gov fetch ...

_audit_ms = int((_time.time() - _audit_start) * 1000)
from app.services.audit import log_sec_content_proxy
log_sec_content_proxy(
    request=request,
    endpoint=f"/api/tickers/{ticker}/filings/{accession_no_dashes}/content",
    status=200,
    duration_ms=_audit_ms,
    details={
        "ticker": ticker,
        "accession_number": accession_no_dashes,
        "cik": cik_no_dashes,
        "source": "gcs" if found_in_gcs else "secgov",
        "content_length": len(content),
    },
)
```

**Gate 2 — Verify SEC proxy audit logging:**
- [ ] SEC content proxy requests appear in structured JSON file log
- [ ] File log contains `user_key`, `method`, `path`, `status`, `duration_ms`, `details`
- [ ] Anonymous requests logged to file (not PostgreSQL)
- [ ] Authenticated requests logged to both file and PostgreSQL

---

## **SUBLAYER 10.3 — Middleware Registration**

### **Step 5: Register audit middleware in app/main.py**

In `app/main.py`:
```python
# After AuthMiddleware registration
from app.middleware.audit_middleware import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

# Update /health endpoint
@app.get("/health")
def health_check() -> dict:
    from app.services.db_access_counter import get_counters
    counters = get_counters()
    has_db_hits = any(v > 0 for v in counters.values())
    return {
        "status": "ok",
        "db_access_counters": counters,
        "db_access_detected": has_db_hits,
    }
```

### **Step 6: Call setup_logging() at module load**

Add at top of `app/main.py`:
```python
from app.logging_config import setup_logging
setup_logging()
```

**Gate 3 — Verify middleware registration:**
- [ ] `AuditLogMiddleware` registered after `AuthMiddleware`
- [ ] `setup_logging()` called at module import
- [ ] `/health` returns `db_access_counters` and `db_access_detected`

---

## **SUBLAYER 10.4 — Query & Consumption Patterns**

### **File-based audit log queries**

```bash
# All SEC proxy access for a user (last 24h)
jq 'select(.user_key=="firebase_uid") | select(.timestamp > (now - 86400))' /var/log/ftd-api/sec-content-proxy.log

# Count by source (GCS vs SEC.gov)
jq -r '.details.source' /var/log/ftd-api/sec-content-proxy.log | sort | uniq -c

# Average response time
jq '.duration_ms' /var/log/ftd-api/sec-content-proxy.log | awk '{s+=$1; n++} END {print s/n}'
```

### **PostgreSQL audit log queries**

```sql
-- All API requests by user (last hour)
SELECT user_key, endpoint, http_method, response_status, response_time_ms, requested_at
FROM api_usage_log
WHERE requested_at > NOW() - INTERVAL '1 hour'
ORDER BY requested_at DESC;

-- Endpoint usage volume (last 24h)
SELECT endpoint, COUNT(*) as request_count, AVG(response_time_ms) as avg_ms
FROM api_usage_log
WHERE requested_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
ORDER BY request_count DESC;
```

**Gate 4 — Verify logging patterns:**
- [ ] File log queries work with `jq`
- [ ] PostgreSQL queries work via `psql`
- [ ] User attribution correct in both channels

---

## **SUBLAYER 10.5 — Post-Implementation Verification**

**Gate 5 — Verify log consumption:**
- [ ] File log contains structured JSON entries (stdout handler; file handler works on GCE VM)
- [ ] PostgreSQL audit table receives inserts for authenticated requests (via `AuditLogMiddleware` → `log_api_request()`)
- [ ] User fingerprints correctly attributed (firebase_uid or user_id → `get_user_fingerprint()` in `user_fingerprint.py`)
- [ ] Anonymous requests logged to file only (SEC proxy endpoints use `user_key = "anonymous"`)
- [ ] Query patterns documented above work (file log `jq` + PostgreSQL SQL documented)

---

## **What to do if any gate fails**

If any verification gate fails, the agent must:
1. Stop all execution
2. Report the failing gate, the exact error, and what was inspected
3. Check database connectivity (port 5432 IAP tunnel)
4. Fix the issue and retry