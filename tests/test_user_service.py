from __future__ import annotations

import unittest
from uuid import uuid4

import psycopg2

from app.auth.hasher import hash_password
from app.auth.models import UserCreateRequest, UserUpdateRequest, normalize_email
from app.db import get_connection
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.services.user_service import (
    create_user,
    delete_user,
    get_authenticated_user,
    get_authenticated_user_by_id,
    get_user_permissions,
    get_user_with_permissions,
    update_user,
)


def _postgres_available() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.users')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT to_regclass('public.permissions')")
                if cur.fetchone()[0] is None:
                    return False
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def _setup_permissions() -> None:
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO permissions (name) VALUES (%s) ON CONFLICT DO NOTHING",
                ("tickers.search",),
            )
            cur.execute(
                "INSERT INTO permissions (name) VALUES (%s) ON CONFLICT DO NOTHING",
                ("tickers.prices",),
            )
            cur.execute(
                "INSERT INTO permissions (name) VALUES (%s) ON CONFLICT DO NOTHING",
                ("search.read",),
            )
        conn.commit()


def _assign_permissions(user_id: int, permission_names: list[str]) -> None:
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM permissions WHERE name = ANY(%s)", (permission_names,))
            perm_map = {row[1]: row[0] for row in cur.fetchall()}
            for name in permission_names:
                perm_id = perm_map.get(name)
                if perm_id is not None:
                    cur.execute(
                        "INSERT INTO user_permissions (user_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (user_id, perm_id),
                    )
        conn.commit()


def _cleanup_user(firebase_uid: str) -> None:
    try:
        with get_connection() as conn:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE firebase_uid = %s", (firebase_uid,))
                row = cur.fetchone()
                if row:
                    user_id = row[0]
                    cur.execute("DELETE FROM user_permissions WHERE user_id = %s", (user_id,))
                    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    except Exception:
        pass


class TestUserService(unittest.TestCase):
    def setUp(self) -> None:
        _setup_permissions()

    def _make_create_request(self, email: str, password: str, firebase_uid: str | None = None) -> UserCreateRequest:
        return UserCreateRequest(email=email, password=password, firebase_uid=firebase_uid)

    def _make_update_request(self, email: str | None = None, is_active: bool | None = None) -> UserUpdateRequest:
        return UserUpdateRequest(email=email, is_active=is_active)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_returns_user_for_valid_firebase_uid(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        user = get_authenticated_user(firebase_uid)

        self.assertIsInstance(user, User)
        self.assertEqual(user.firebase_uid, firebase_uid)
        self.assertEqual(user.email, normalize_email(email))
        self.assertEqual(user.id, created.id)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_raises_for_unknown_firebase_uid(self) -> None:
        with self.assertRaises(UserNotFoundError) as ctx:
            get_authenticated_user("nonexistent-firebase-uid")
        self.assertIn("nonexistent-firebase-uid", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_by_id_returns_user_for_valid_id(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        user = get_authenticated_user_by_id(created.id)

        self.assertIsInstance(user, User)
        self.assertEqual(user.id, created.id)
        self.assertEqual(user.email, normalize_email(email))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_by_id_raises_for_unknown_id(self) -> None:
        with self.assertRaises(UserNotFoundError) as ctx:
            get_authenticated_user_by_id(99999)
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_permissions_returns_empty_for_user_without_permissions(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        permissions = get_user_permissions(created.id)
        self.assertEqual(permissions, [])

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permissions_returns_user_and_permissions(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        _assign_permissions(created.id, ["tickers.search", "tickers.prices"])

        from app.auth.index_maintainer import sync_user_permissions_index
        sync_user_permissions_index(created.id)

        response = get_user_with_permissions(created.id)
        self.assertIsInstance(response, type(created))
        self.assertEqual(response.id, created.id)
        self.assertEqual(response.email, normalize_email(email))
        self.assertIn("tickers.search", response.permissions)
        self.assertIn("tickers.prices", response.permissions)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permissions_raises_for_unknown_id(self) -> None:
        with self.assertRaises(UserNotFoundError) as ctx:
            get_user_with_permissions(99999)
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_create_user_creates_new_user(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        user = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, normalize_email(email))
        self.assertEqual(user.firebase_uid, firebase_uid)
        self.assertTrue(user.is_active)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email, firebase_uid, is_active FROM users WHERE id = %s", (user.id,))
                row = cur.fetchone()
                self.assertEqual(row[0], normalize_email(email))
                self.assertEqual(row[1], firebase_uid)
                self.assertTrue(row[2])

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_create_user_raises_for_duplicate_email(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        with self.assertRaises(UserAlreadyExistsError):
            create_user(self._make_create_request(email=email, password="another-pass", firebase_uid=None))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_create_user_raises_for_duplicate_firebase_uid(self) -> None:
        firebase_uid = uuid4().hex
        email1 = f"test1-{uuid4().hex}@example.com"
        email2 = f"test2-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        create_user(self._make_create_request(email=email1, password="test-pass", firebase_uid=firebase_uid))
        with self.assertRaises(UserAlreadyExistsError):
            create_user(self._make_create_request(email=email2, password="another-pass", firebase_uid=firebase_uid))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_update_user_modifies_email_and_active_status(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        updated = update_user(created.id, self._make_update_request(email="updated@example.com", is_active=False))

        self.assertEqual(updated.id, created.id)
        self.assertEqual(updated.email, normalize_email("updated@example.com"))
        self.assertFalse(updated.is_active)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_update_user_raises_for_unknown_id(self) -> None:
        with self.assertRaises(UserNotFoundError) as ctx:
            update_user(99999, self._make_update_request(email="updated@example.com"))
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_update_user_raises_for_duplicate_email(self) -> None:
        firebase_uid1 = uuid4().hex
        firebase_uid2 = uuid4().hex
        email1 = f"first-{uuid4().hex}@example.com"
        email2 = f"second-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid1)
        self.addCleanup(_cleanup_user, firebase_uid2)

        first = create_user(self._make_create_request(email=email1, password="test-pass", firebase_uid=firebase_uid1))
        second = create_user(self._make_create_request(email=email2, password="test-pass", firebase_uid=firebase_uid2))

        with self.assertRaises(UserAlreadyExistsError):
            update_user(second.id, self._make_update_request(email=first.email))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_delete_user_deactivates_active_user(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        result = delete_user(created.id)
        self.assertTrue(result)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT is_active FROM users WHERE id = %s", (created.id,))
                self.assertFalse(cur.fetchone()[0])

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_delete_user_returns_false_for_already_inactive_user(self) -> None:
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        with get_connection() as conn:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (created.id,))
            conn.commit()

        result = delete_user(created.id)
        self.assertFalse(result)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_delete_user_returns_false_for_unknown_user(self) -> None:
        result = delete_user(99999)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
