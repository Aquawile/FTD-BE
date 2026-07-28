from __future__ import annotations

import os

JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES: int = int(os.environ.get("JWT_EXPIRATION_MINUTES", "60"))
JWT_ISSUER: str = os.environ.get("JWT_ISSUER", "ftd-auth")
JWT_AUDIENCE: str = os.environ.get("JWT_AUDIENCE", "ftd-api")
JWT_TOKEN_VERSION: int = int(os.environ.get("JWT_TOKEN_VERSION", "1"))
BCRYPT_ROUNDS: int = int(os.environ.get("BCRYPT_ROUNDS", "12"))


def get_jwt_settings() -> dict[str, object]:
    return {
        "secret_key": JWT_SECRET_KEY,
        "algorithm": JWT_ALGORITHM,
        "expiration_minutes": JWT_EXPIRATION_MINUTES,
        "issuer": JWT_ISSUER,
        "audience": JWT_AUDIENCE,
        "token_version": JWT_TOKEN_VERSION,
        "bcrypt_rounds": BCRYPT_ROUNDS,
    }