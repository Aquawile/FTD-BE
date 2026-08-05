from __future__ import annotations

import logging
from typing import Any, Mapping

import psycopg2
import psycopg2.extras

from app.auth.models import User, normalize_email
from app.db import get_connection

logger = logging.getLogger(__name__)


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
        logger.error("user_sync_failed: reason=missing_firebase_uid identity=%s", verified_identity.get("firebase_uid"))
        raise ValueError("firebase_uid is required")

    email = verified_identity.get("email")
    normalized_email = normalize_email(email) if isinstance(email, str) else ""
    if not normalized_email:
        logger.error("user_sync_failed: reason=missing_email firebase_uid=%s", firebase_uid)
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
                logger.info("user_sync_reused: firebase_uid=%s user_id=%s", firebase_uid, existing_row["id"])
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
                    logger.error("user_sync_failed: reason=database_error firebase_uid=%s", firebase_uid, exc_info=True)
                    raise

                cur.execute(
                    "SELECT id, firebase_uid, email, is_active, created_at, updated_at "
                    "FROM users WHERE firebase_uid = %s",
                    (firebase_uid,),
                )
                existing_row = cur.fetchone()
                if existing_row is None:
                    logger.error("user_sync_failed: reason=integrity_error_no_row firebase_uid=%s", firebase_uid)
                    raise
                logger.info("user_sync_reused: firebase_uid=%s user_id=%s", firebase_uid, existing_row["id"])
                return _row_to_user(existing_row)

            if created_row is None:
                logger.error("user_sync_failed: reason=empty_insert_result firebase_uid=%s", firebase_uid)
                raise RuntimeError("Failed to create application user")
            logger.info("user_sync_created: firebase_uid=%s user_id=%s", firebase_uid, created_row["id"])
            return _row_to_user(created_row)
