from __future__ import annotations

from typing import Any, Mapping

import psycopg2
import psycopg2.extras

from app.auth.models import User, normalize_email
from app.db import get_connection


def _row_to_user(row: Mapping[str, Any]) -> User:
    return User(
        id=row["id"],
        firebase_uid=row.get("firebase_uid"),
        email=row["email"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def synchronize_user(verified_identity: Mapping[str, Any]) -> User:
    """Synchronize a verified Firebase identity to the PostgreSQL users table."""
    firebase_uid = verified_identity.get("firebase_uid")
    if not isinstance(firebase_uid, str) or not firebase_uid.strip():
        raise ValueError("firebase_uid is required")

    email = verified_identity.get("email")
    normalized_email = normalize_email(email) if isinstance(email, str) else ""
    if not normalized_email:
        raise ValueError("email is required")

    firebase_uid = firebase_uid.strip()

    with get_connection() as conn:
        conn.rollback()
        conn.autocommit = False

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, firebase_uid, email, is_active, created_at, updated_at "
                "FROM users WHERE firebase_uid = %s",
                (firebase_uid,),
            )
            existing_row = cur.fetchone()
            if existing_row is not None:
                conn.commit()
                return _row_to_user(existing_row)

            try:
                cur.execute(
                    "INSERT INTO users (firebase_uid, email) VALUES (%s, %s) "
                    "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
                    (firebase_uid, normalized_email),
                )
                created_row = cur.fetchone()
                conn.commit()
            except psycopg2.IntegrityError as exc:
                conn.rollback()
                if getattr(exc, "pgcode", None) != "23505":
                    raise

                cur.execute(
                    "SELECT id, firebase_uid, email, is_active, created_at, updated_at "
                    "FROM users WHERE firebase_uid = %s",
                    (firebase_uid,),
                )
                existing_row = cur.fetchone()
                if existing_row is None:
                    raise
                return _row_to_user(existing_row)

            if created_row is None:
                raise RuntimeError("Failed to create application user")
            return _row_to_user(created_row)
