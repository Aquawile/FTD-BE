import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg2

from app.auth import firebase_auth as firebase_auth_module
from app.auth.firebase_auth import validate_firebase_token
from app.auth.models import User
from app.auth.user_sync import synchronize_user
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
