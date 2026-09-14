from __future__ import annotations

import logging
from typing import Any, Mapping

import psycopg2
import psycopg2.extras

from app.auth.models import User, normalize_email
from app.db import get_connection

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS = [
    "tickers.search",
    "tickers.prices",
    "tickers.news",
    "tickers.filings",
    "tickers.timeline",
    "tickers.fiscal_year_end",
    "filings.read",
    "search.read",
    "dashboard.read",
]


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
            except psycopg2.IntegrityError as exc:
                conn.rollback()
                if getattr(exc, "pgcode", None) != "23505":
                    logger.error("user_sync_failed: reason=database_error firebase_uid=%s", firebase_uid, exc_info=True)
                    raise

                constraint_name = getattr(getattr(exc, "diag", None), "constraint_name", "") or ""
                if constraint_name == "users_email_key":
                    cur.execute(
                        "UPDATE users SET firebase_uid = %s WHERE email = %s "
                        "RETURNING id, firebase_uid, email, is_active, created_at, updated_at",
                        (firebase_uid, normalized_email),
                    )
                    linked_row = cur.fetchone()
                    if linked_row is not None:
                        linked_user_id = linked_row["id"]
                        for perm_name in DEFAULT_PERMISSIONS:
                            cur.execute(
                                "INSERT INTO user_permissions (user_id, permission_id) "
                                "SELECT %s, permissions.id FROM permissions WHERE permissions.name = %s "
                                "ON CONFLICT (user_id, permission_id) DO NOTHING",
                                (linked_user_id, perm_name),
                            )
                        conn.commit()
                        from app.auth.index_maintainer import sync_user_permissions_index
                        sync_user_permissions_index(linked_user_id)
                        logger.info("user_sync_linked: firebase_uid=%s user_id=%s granted=%d", firebase_uid, linked_user_id, len(DEFAULT_PERMISSIONS))
                        return _row_to_user(linked_row)

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

            new_user_id = created_row["id"]
            for perm_name in DEFAULT_PERMISSIONS:
                cur.execute(
                    "INSERT INTO user_permissions (user_id, permission_id) "
                    "SELECT %s, permissions.id FROM permissions WHERE permissions.name = %s "
                    "ON CONFLICT (user_id, permission_id) DO NOTHING",
                    (new_user_id, perm_name),
                )
            conn.commit()
            from app.auth.index_maintainer import sync_user_permissions_index
            sync_user_permissions_index(new_user_id)
            logger.info("user_sync_created: firebase_uid=%s user_id=%s permissions=%d", firebase_uid, new_user_id, len(DEFAULT_PERMISSIONS))
            return _row_to_user(created_row)
