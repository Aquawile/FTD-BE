from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.auth.config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_EXPIRATION_MINUTES,
    JWT_ISSUER,
    JWT_SECRET_KEY,
    JWT_TOKEN_VERSION,
)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = dict(data)
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES))
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "tv": JWT_TOKEN_VERSION,
        }
    )
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        if payload.get("tv") != JWT_TOKEN_VERSION:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None