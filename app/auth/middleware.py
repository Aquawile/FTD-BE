from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.exceptions import AuthenticationError, AuthenticationInternalError
from app.auth.firebase_auth import validate_firebase_token_with_reason

logger = logging.getLogger(__name__)


PUBLIC_PATHS = {
    "/health",
    "/version",
    "/auth/me",
    "/dashboard/stats",
    "/tickers/tracked",
    "/auth/account-exists",
}

SEC_PROXY_PREFIX = "/tickers/"
SEC_PROXY_SUFFIX = "/content"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if (
            path in PUBLIC_PATHS
            or (path.startswith(SEC_PROXY_PREFIX) and path.endswith(SEC_PROXY_SUFFIX))
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header is None:
            logger.warning("authentication_failed: reason=missing_authorization_header path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"},
            )

        if not auth_header.startswith("Bearer "):
            logger.warning("authentication_failed: reason=invalid_header_format path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization header format"},
            )

        token = auth_header[len("Bearer ") :]
        if not token:
            logger.warning("authentication_failed: reason=empty_token path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing token"},
            )

        firebase_user, firebase_reason = validate_firebase_token_with_reason(token)
        if firebase_user is not None:
            firebase_uid = firebase_user.get("firebase_uid")
            if not firebase_uid:
                logger.warning("authentication_failed: reason=firebase_uid_missing path=%s", path)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authenticated Firebase token did not contain a UID"},
                )
            request.state.firebase_uid = firebase_uid
            request.state.email = firebase_user.get("email")
            request.state.email_verified = firebase_user.get("email_verified")
            request.state.auth_method = "firebase"
            logger.info("authentication_succeeded: method=firebase firebase_uid=%s path=%s", firebase_uid, path)
            return await call_next(request)

        # Firebase is the only sign-in method (project ftd-2026).
        if firebase_reason == "expired":
            logger.warning("authentication_failed: reason=firebase_token_expired path=%s", path)
        elif firebase_reason == "invalid":
            logger.warning("authentication_failed: reason=firebase_token_invalid path=%s", path)
        else:
            logger.warning("authentication_failed: reason=firebase_token_unknown path=%s", path)
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )
