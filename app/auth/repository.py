from __future__ import annotations

from app.auth.models import normalize_email
from app.db import query, query_dict


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


def create_user(email: str, password_hash: str, firebase_uid: str | None) -> dict:
    """Insert a new user record and return the created row."""
    rows = query_dict(
        "INSERT INTO users (email, password_hash, firebase_uid) VALUES (%s, %s, %s) "
        "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
        (email, password_hash, firebase_uid),
    )
    if not rows:
        raise RuntimeError("Failed to create user")
    return rows[0]


def update_user(user_id: int, email: str | None, is_active: bool | None) -> dict | None:
    """Update a user's application-owned fields and return the updated row."""
    updates = []
    params = []
    if email is not None:
        updates.append("email = %s")
        params.append(email)
    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)
    if not updates:
        return get_user_by_id(user_id)
    params.append(user_id)
    rows = query_dict(
        f"UPDATE users SET {', '.join(updates)} WHERE id = %s "
        "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
        tuple(params),
    )
    if not rows:
        return None
    return rows[0]


def deactivate_user(user_id: int) -> bool:
    """Soft-delete a user by setting is_active to FALSE. Returns True if a row was updated."""
    result = query(
        "UPDATE users SET is_active = FALSE WHERE id = %s AND is_active = TRUE RETURNING id",
        (user_id,),
    )
    return len(result) > 0
