"""User fingerprinting — extracts identity from request.state.

Returns (user_key, auth_method) tuple for audit logging.
"""
from typing import Any
from fastapi import Request


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
