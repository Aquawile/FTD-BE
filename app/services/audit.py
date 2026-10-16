"""Audit logging utility — records API requests to PostgreSQL and file logs.

This module provides:
1. User fingerprint capture (firebase_uid or user_id) from request.state
2. INSERT into api_usage_log table for authenticated requests
3. Structured file logging for SEC proxy access (anonymous requests)

This is the ONLY non-vectorized-data database operation in the migration.
"""
import json
import logging
import time
from fastapi import Request

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")


def log_api_request(request: Request, response_status: int, response_time_ms: int,
                    query_params: dict | None = None,
                    path_params: dict | None = None,
                    request_body: dict | None = None) -> None:
    """Insert an API request record into the api_usage_log table.

    Only logs authenticated requests (non-anonymous).
    """
    from app.services.user_fingerprint import get_user_fingerprint
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
    from app.services.user_fingerprint import get_user_fingerprint

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
