"""Audit logging middleware — wraps each request with audit logging.

Registered AFTER AuthMiddleware so request.state is populated with
user identity information.
"""
import time
import logging
from fastapi import Request, Response
from starlette.concurrency import run_in_threadpool
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
            # A blocking DB write must not run on the event loop (it would stall every other request).
            await run_in_threadpool(log_api_request, request, status_code, elapsed_ms,
                                    query_params=query_params, path_params=path_params)
        except Exception as e:
            logger.warning("audit_middleware_error: %s", e)
