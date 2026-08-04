from __future__ import annotations

from app.auth.models import normalize_email
from app.db import query_dict


def get_user_by_email(email: str) -> dict | None:
    normalized = normalize_email(email)
    rows = query_dict(
        "SELECT id, email, password_hash, is_active FROM users WHERE email = %s",
        (normalized,),
    )
    if rows:
        return rows[0]
    return None


def get_user_by_id(user_id: int) -> dict | None:
    rows = query_dict(
        "SELECT id, firebase_uid, email, is_active, created_at, updated_at FROM users WHERE id = %s",
        (user_id,),
    )
    if rows:
        return rows[0]
    return None


def get_user_by_firebase_uid(firebase_uid: str) -> dict | None:
    rows = query_dict(
        "SELECT id, firebase_uid, email, is_active, created_at, updated_at FROM users WHERE firebase_uid = %s",
        (firebase_uid,),
    )
    if rows:
        return rows[0]
    return None
