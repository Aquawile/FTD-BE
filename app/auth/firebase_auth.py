from __future__ import annotations

from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.auth.exceptions import AuthenticationError
from app.auth.firebase_config import FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID

_firebase_initialized: bool = False


def _initialize_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return
    if FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    else:
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
    _firebase_initialized = True


def validate_firebase_token(token: str) -> dict[str, Any] | None:
    validated, _ = validate_firebase_token_with_reason(token)
    return validated


def validate_firebase_token_with_reason(token: str) -> tuple[dict[str, Any] | None, str | None]:
    _initialize_firebase()
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return (
            {
                "firebase_uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "email_verified": decoded_token.get("email_verified", False),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
                "issuer": decoded_token.get("iss"),
                "audience": decoded_token.get("aud"),
                "auth_time": decoded_token.get("auth_time"),
            },
            None,
        )
    except firebase_auth.InvalidIdTokenError:
        return None, "invalid"
    except firebase_auth.ExpiredIdTokenError:
        return None, "expired"
    except Exception:
        return None, "invalid"


def get_firebase_user(uid: str) -> dict[str, Any] | None:
    _initialize_firebase()
    try:
        user = firebase_auth.get_user(uid)
        return {
            "firebase_uid": user.uid,
            "email": user.email,
            "email_verified": user.email_verified,
            "name": user.display_name,
            "picture": user.photo_url,
            "disabled": user.disabled,
        }
    except firebase_auth.UserNotFoundError:
        return None
    except Exception:
        return None