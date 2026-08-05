from __future__ import annotations

import psycopg2
import psycopg2.extras

from app.auth.models import normalize_email
from app.db import get_connection, query_dict


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
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, firebase_uid) VALUES (%s, %s, %s) "
                "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
                (email, password_hash, firebase_uid),
            )
            row = cur.fetchone()
            conn.commit()
            if row is None:
                raise RuntimeError("Failed to create user")
            return dict(row)


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
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = %s "
                "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
                tuple(params),
            )
            row = cur.fetchone()
            conn.commit()
            if row is None:
                return None
            return dict(row)


def get_user_with_permissions(user_id: int) -> dict | None:
    """Retrieve a user and their permission names in a single relational query.

    This joins the ``users`` table with ``user_permissions_index`` on the
    foreign-key column ``user_permissions_index.user_id`` referencing
    ``users.id``. The query selects only the fields required by the
    application response contract, avoiding an entire table scan or
    unnecessary column retrieval.
    """
    rows = query_dict(
        "SELECT u.id, u.firebase_uid, u.email, u.is_active, u.created_at, u.updated_at, "
        "ARRAY_AGG(upi.permission_name) AS permissions "
        "FROM users u "
        "LEFT JOIN user_permissions_index upi ON upi.user_id = u.id "
        "WHERE u.id = %s "
        "GROUP BY u.id, u.firebase_uid, u.email, u.is_active, u.created_at, u.updated_at",
        (user_id,),
    )
    if rows:
        return rows[0]
    return None


def deactivate_user(user_id: int) -> bool:
    """Soft-delete a user by setting is_active to FALSE. Returns True if a row was updated."""
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = FALSE WHERE id = %s AND is_active = TRUE RETURNING id",
                (user_id,),
            )
            row = cur.fetchone()
            conn.commit()
            return row is not None
