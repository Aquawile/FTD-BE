import os
import pytest
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg2

from app.auth import firebase_auth as firebase_auth_module
from app.auth.firebase_auth import validate_firebase_token
from app.auth.models import User
from app.auth.user_sync import synchronize_user, DEFAULT_PERMISSIONS
from app.db import get_connection


def _postgres_available() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.users')")
                table_name = cur.fetchone()[0]
                if table_name is None:
                    return False
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


@pytest.mark.db_integration
class TestUserSync(unittest.TestCase):
    @staticmethod
    def _cleanup_user(firebase_uid: str) -> None:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE firebase_uid = %s", (firebase_uid,))
                    conn.commit()
        except Exception:
            pass

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_new_firebase_identity_creates_postgres_user(self) -> None:
        firebase_uid = uuid4().hex
        email = "new.user@example.com"

        self.addCleanup(self._cleanup_user, firebase_uid)

        user = synchronize_user({"firebase_uid": firebase_uid, "email": email})

        self.assertIsInstance(user, User)
        self.assertEqual(user.firebase_uid, firebase_uid)
        self.assertEqual(user.email, email.lower())
        self.assertIsNotNone(user.id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users WHERE firebase_uid = %s", (firebase_uid,))
                self.assertEqual(cur.fetchone()[0], 1)
                cur.execute("SELECT email FROM users WHERE firebase_uid = %s", (firebase_uid,))
                self.assertEqual(cur.fetchone()[0], email.lower())

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_existing_firebase_identity_is_reused(self) -> None:
        firebase_uid = uuid4().hex
        self.addCleanup(self._cleanup_user, firebase_uid)

        first = synchronize_user({"firebase_uid": firebase_uid, "email": "first@example.com"})
        second = synchronize_user({"firebase_uid": firebase_uid, "email": "second@example.com"})

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.firebase_uid, firebase_uid)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users WHERE firebase_uid = %s", (firebase_uid,))
                self.assertEqual(cur.fetchone()[0], 1)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_firebase_uid_is_the_identity_key(self) -> None:
        firebase_uid = uuid4().hex
        self.addCleanup(self._cleanup_user, firebase_uid)

        first = synchronize_user({"firebase_uid": firebase_uid, "email": "first@example.com"})
        second = synchronize_user({"firebase_uid": firebase_uid, "email": "different@example.com"})

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.firebase_uid, firebase_uid)
        self.assertNotEqual(first.email, "different@example.com")

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_different_firebase_uid_with_same_email_is_linked(self) -> None:
        email = "same.email@example.com"
        uid_a = uuid4().hex
        uid_b = uuid4().hex
        self.addCleanup(self._cleanup_user, uid_a)
        self.addCleanup(self._cleanup_user, uid_b)

        user_a = synchronize_user({"firebase_uid": uid_a, "email": email})
        user_b = synchronize_user({"firebase_uid": uid_b, "email": email})

        self.assertEqual(user_a.email, user_b.email)
        self.assertEqual(user_a.id, user_b.id)
        self.assertEqual(user_b.firebase_uid, uid_b)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_new_user_gets_default_permissions(self) -> None:
        firebase_uid = uuid4().hex
        email = "perms.test@example.com"

        self.addCleanup(self._cleanup_user, firebase_uid)

        user = synchronize_user({"firebase_uid": firebase_uid, "email": email})
        self.assertIsNotNone(user.id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT permission_name FROM user_permissions_index WHERE user_id = %s",
                    (user.id,),
                )
                granted = {row[0] for row in cur.fetchall()}
                for perm in DEFAULT_PERMISSIONS:
                    self.assertIn(perm, granted, f"Missing default permission: {perm}")

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_user_with_no_permissions_is_healed_and_partial_user_untouched(self) -> None:
        import asyncio

        from app.auth.dependencies import get_current_permissions

        empty_uid, partial_uid = uuid4().hex, uuid4().hex
        self.addCleanup(self._cleanup_user, empty_uid)
        self.addCleanup(self._cleanup_user, partial_uid)

        with get_connection() as conn:
            with conn.cursor() as cur:
                ids = []
                for uid, mail in ((empty_uid, "legacy.empty@example.com"), (partial_uid, "legacy.partial@example.com")):
                    cur.execute("INSERT INTO users (firebase_uid, email) VALUES (%s, %s) RETURNING id", (uid, mail))
                    ids.append(cur.fetchone()[0])
                cur.execute(
                    "INSERT INTO user_permissions (user_id, permission_id) "
                    "SELECT %s, id FROM permissions WHERE name = 'dashboard.read'",
                    (ids[1],),
                )
                conn.commit()
        from datetime import datetime
        now = datetime.now()
        empty_user = User(id=ids[0], firebase_uid=empty_uid, email="legacy.empty@example.com",
                          is_active=True, created_at=now, updated_at=now)
        partial_user = User(id=ids[1], firebase_uid=partial_uid, email="legacy.partial@example.com",
                            is_active=True, created_at=now, updated_at=now)

        healed = asyncio.run(get_current_permissions(empty_user))
        self.assertEqual(healed, set(DEFAULT_PERMISSIONS))
        self.assertEqual(asyncio.run(get_current_permissions(empty_user)), set(DEFAULT_PERMISSIONS))
        self.assertEqual(asyncio.run(get_current_permissions(partial_user)), {"dashboard.read"})

    def test_missing_firebase_uid_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            synchronize_user({"email": "test@example.com"})

    def test_invalid_firebase_token_is_rejected_before_sync(self) -> None:
        with patch.object(firebase_auth_module, "_initialize_firebase"), patch.object(
            firebase_auth_module.firebase_auth,
            "verify_id_token",
            side_effect=firebase_auth_module.firebase_auth.InvalidIdTokenError("bad token"),
        ):
            result = validate_firebase_token("not-a-real-token")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
