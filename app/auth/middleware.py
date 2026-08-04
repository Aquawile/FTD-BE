from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.firebase_auth import validate_firebase_token
from app.auth.token import verify_token


PUBLIC_PATHS = {"/health", "/auth/login", "/auth/me"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs") or path == "/openapi.json" or path == "/redoc":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"},
            )

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization header format"},
            )

        token = auth_header[len("Bearer ") :]
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing token"},
            )

        firebase_user = validate_firebase_token(token)
        if firebase_user is not None:
            request.state.firebase_uid = firebase_user.get("firebase_uid")
            request.state.email = firebase_user.get("email")
            request.state.auth_method = "firebase"
            return await call_next(request)

        payload = verify_token(token)
        if payload is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None or email is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token missing required claims"},
            )

        try:
            request.state.user_id = int(user_id)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid user identifier in token"},
            )
        request.state.email = email
        request.state.auth_method = "internal"

        return await call_next(request)