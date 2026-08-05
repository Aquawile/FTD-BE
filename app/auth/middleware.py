from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.exceptions import AuthenticationError, AuthenticationInternalError
from app.auth.firebase_auth import validate_firebase_token_with_reason
from app.auth.models import User
from app.auth.repository import get_user_by_firebase_uid, get_user_by_id
from app.auth.token import verify_token

logger = logging.getLogger(__name__)


PUBLIC_PATHS = {"/health", "/auth/login", "/auth/me"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs") or path == "/openapi.json" or path == "/redoc":
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
            request.state.auth_method = "firebase"
            try:
                user_data = get_user_by_firebase_uid(firebase_uid)
            except Exception:
                logger.error("authentication_internal_error: reason=postgres_lookup_failed firebase_uid=%s path=%s", firebase_uid, path, exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error"},
                )
            if user_data is None:
                logger.warning("authentication_failed: reason=postgres_user_not_found firebase_uid=%s path=%s", firebase_uid, path)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authenticated Firebase identity has no associated application user"},
                )
            request.state.current_user = User(**user_data)
            logger.info("authentication_succeeded: method=firebase firebase_uid=%s user_id=%s path=%s", firebase_uid, user_data["id"], path)
            return await call_next(request)

        if firebase_reason == "expired":
            logger.warning("authentication_failed: reason=firebase_token_expired path=%s", path)
        else:
            logger.warning("authentication_failed: reason=firebase_token_invalid path=%s", path)

        payload = verify_token(token)
        if payload is None:
            logger.warning("authentication_failed: reason=invalid_or_expired_internal_token path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            logger.warning("authentication_failed: reason=token_missing_claims path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Token missing required claims"},
            )

        try:
            resolved_user_id = int(user_id)
        except (ValueError, TypeError):
            logger.warning("authentication_failed: reason=invalid_user_identifier path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid user identifier in token"},
            )
        request.state.user_id = resolved_user_id
        request.state.email = email
        request.state.auth_method = "internal"
        try:
            user_data = get_user_by_id(resolved_user_id)
        except Exception:
            logger.error("authentication_internal_error: reason=postgres_lookup_failed user_id=%s path=%s", resolved_user_id, path, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        if user_data is None:
            logger.warning("authentication_failed: reason=postgres_user_not_found user_id=%s path=%s", resolved_user_id, path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Authenticated token has no associated application user"},
            )
        request.state.current_user = User(**user_data)
        logger.info("authentication_succeeded: method=internal user_id=%s path=%s", resolved_user_id, path)

        return await call_next(request)