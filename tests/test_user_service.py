from __future__ import annotations

import logging
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg2

from app.auth import firebase_auth as firebase_auth_module
from app.auth.hasher import hash_password
from app.auth.models import User, UserCreateRequest, UserPermissionsResponse, UserUpdateRequest, UserWithPermissionDetails, normalize_email
from app.auth.user_sync import synchronize_user
from app.db import get_connection
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError, UserValidationError
from app.services.user_service import (
    create_user,
    delete_user,
    get_authenticated_user,
    get_authenticated_user_by_id,
    get_user_permissions,
    get_user_with_permission_details,
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
    def _make_create_request(self, email: str, password: str, firebase_uid: str | None = None) -> UserCreateRequest:
        return UserCreateRequest(email=email, password=password, firebase_uid=firebase_uid)

    def _make_update_request(self, email: str | None = None, is_active: bool | None = None) -> UserUpdateRequest:
        return UserUpdateRequest(email=email, is_active=is_active)

    # --- Validation tests (do not require PostgreSQL) ---

    def test_create_user_raises_for_empty_email(self) -> None:
        with self.assertRaises(UserValidationError) as ctx:
            create_user(self._make_create_request(email="", password="test-pass"))
        self.assertIn("empty", str(ctx.exception).lower())

    def test_create_user_raises_for_short_password(self) -> None:
        with self.assertRaises(UserValidationError) as ctx:
            create_user(self._make_create_request(email="valid@example.com", password="short"))
        self.assertIn("at least 8", str(ctx.exception))

    def test_create_user_raises_for_invalid_firebase_uid(self) -> None:
        with self.assertRaises(UserValidationError) as ctx:
            create_user(self._make_create_request(email="valid@example.com", password="test-pass", firebase_uid="short"))
        self.assertIn("Firebase UID", str(ctx.exception))

    def test_update_user_raises_when_no_fields_provided(self) -> None:
        with self.assertRaises(UserValidationError) as ctx:
            update_user(1, self._make_update_request())
        self.assertIn("at least one", str(ctx.exception).lower())

    def test_update_user_raises_for_empty_email(self) -> None:
        with self.assertRaises(UserValidationError) as ctx:
            update_user(1, self._make_update_request(email="  "))
        self.assertIn("empty", str(ctx.exception).lower())

    # --- PostgreSQL integration tests ---

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_returns_user_for_valid_firebase_uid(self) -> None:
        _setup_permissions()
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
        _setup_permissions()
        with self.assertRaises(UserNotFoundError) as ctx:
            get_authenticated_user("nonexistent-firebase-uid")
        self.assertIn("nonexistent-firebase-uid", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_authenticated_user_by_id_returns_user_for_valid_id(self) -> None:
        _setup_permissions()
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
        _setup_permissions()
        with self.assertRaises(UserNotFoundError) as ctx:
            get_authenticated_user_by_id(99999)
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_permissions_returns_empty_for_user_without_permissions(self) -> None:
        _setup_permissions()
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        permissions = get_user_permissions(created.id)
        self.assertEqual(permissions, [])

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permissions_returns_user_and_permissions(self) -> None:
        _setup_permissions()
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        _assign_permissions(created.id, ["tickers.search", "tickers.prices"])

        from app.auth.index_maintainer import sync_user_permissions_index
        sync_user_permissions_index(created.id)

        response = get_user_with_permissions(created.id)
        self.assertIsInstance(response, UserPermissionsResponse)
        self.assertEqual(response.id, created.id)
        self.assertEqual(response.email, normalize_email(email))
        self.assertIn("tickers.search", response.permissions)
        self.assertIn("tickers.prices", response.permissions)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permissions_raises_for_unknown_id(self) -> None:
        _setup_permissions()
        with self.assertRaises(UserNotFoundError) as ctx:
            get_user_with_permissions(99999)
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_create_user_creates_new_user(self) -> None:
        _setup_permissions()
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
        _setup_permissions()
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        with self.assertRaises(UserAlreadyExistsError):
            create_user(self._make_create_request(email=email, password="another-pass", firebase_uid=None))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_create_user_raises_for_duplicate_firebase_uid(self) -> None:
        _setup_permissions()
        firebase_uid = uuid4().hex
        email1 = f"test1-{uuid4().hex}@example.com"
        email2 = f"test2-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        create_user(self._make_create_request(email=email1, password="test-pass", firebase_uid=firebase_uid))
        with self.assertRaises(UserAlreadyExistsError):
            create_user(self._make_create_request(email=email2, password="another-pass", firebase_uid=firebase_uid))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_update_user_modifies_email_and_active_status(self) -> None:
        _setup_permissions()
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
        _setup_permissions()
        with self.assertRaises(UserNotFoundError) as ctx:
            update_user(99999, self._make_update_request(email="updated@example.com"))
        self.assertIn("99999", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_update_user_raises_for_duplicate_email(self) -> None:
        _setup_permissions()
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
        _setup_permissions()
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
        _setup_permissions()
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
        _setup_permissions()
        result = delete_user(99999)
        self.assertFalse(result)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permission_details_returns_user_with_empty_permissions(self) -> None:
        _setup_permissions()
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        response = get_user_with_permission_details(created.id)
        self.assertIsInstance(response, UserWithPermissionDetails)
        self.assertEqual(response.id, created.id)
        self.assertEqual(response.email, normalize_email(email))
        self.assertEqual(response.permissions, [])

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permission_details_returns_user_with_full_permissions(self) -> None:
        _setup_permissions()
        firebase_uid = uuid4().hex
        email = f"test-{uuid4().hex}@example.com"
        self.addCleanup(_cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        _assign_permissions(created.id, ["tickers.search", "tickers.prices"])

        response = get_user_with_permission_details(created.id)
        self.assertIsInstance(response, UserWithPermissionDetails)
        self.assertEqual(response.id, created.id)
        self.assertEqual(response.email, normalize_email(email))
        self.assertEqual(len(response.permissions), 2)

        names = {p.name for p in response.permissions}
        self.assertIn("tickers.search", names)
        self.assertIn("tickers.prices", names)

        for p in response.permissions:
            self.assertIsInstance(p.id, int)
            self.assertIsInstance(p.name, str)
            self.assertIsInstance(p.description, (str, type(None)))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_get_user_with_permission_details_raises_for_unknown_id(self) -> None:
        _setup_permissions()
        with self.assertRaises(UserNotFoundError) as ctx:
            get_user_with_permission_details(99999)
        self.assertIn("99999", str(ctx.exception))


class TestLayer3Integration(unittest.TestCase):
    """Integration tests verifying the complete Layer Three service-layer sequence."""

    @staticmethod
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
                        cur.execute("DELETE FROM user_permissions_index WHERE user_id = %s", (user_id,))
                        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
        except Exception:
            pass

    def _make_create_request(self, email: str, password: str, firebase_uid: str | None = None) -> UserCreateRequest:
        return UserCreateRequest(email=email, password=password, firebase_uid=firebase_uid)

    def _make_update_request(self, email: str | None = None, is_active: bool | None = None) -> UserUpdateRequest:
        return UserUpdateRequest(email=email, is_active=is_active)

    def _setup_permissions(self) -> None:
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

    def _assign_permissions(self, user_id: int, permission_names: list[str]) -> None:
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

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_complete_user_lifecycle_firebase_sync_to_service_retrieval(self) -> None:
        self._setup_permissions()
        firebase_uid = uuid4().hex
        email = f"lifecycle-{uuid4().hex}@example.com"
        self.addCleanup(self._cleanup_user, firebase_uid)

        with patch.object(firebase_auth_module, "_initialize_firebase"), patch.object(
            firebase_auth_module.firebase_auth,
            "verify_id_token",
            return_value={"firebase_uid": firebase_uid, "email": email},
        ):
            synced_user = synchronize_user({"firebase_uid": firebase_uid, "email": email})

        self.assertIsInstance(synced_user, User)
        self.assertEqual(synced_user.firebase_uid, firebase_uid)
        self.assertEqual(synced_user.email, email.lower())
        self.assertIsNotNone(synced_user.id)

        authenticated_user = get_authenticated_user(firebase_uid)
        self.assertEqual(authenticated_user.id, synced_user.id)
        self.assertEqual(authenticated_user.firebase_uid, firebase_uid)

        self._assign_permissions(authenticated_user.id, ["tickers.search", "tickers.prices"])
        from app.auth.index_maintainer import sync_user_permissions_index
        sync_user_permissions_index(authenticated_user.id)

        with_permissions = get_user_with_permissions(authenticated_user.id)
        self.assertIsInstance(with_permissions, UserPermissionsResponse)
        self.assertEqual(with_permissions.id, authenticated_user.id)
        self.assertEqual(with_permissions.email, email.lower())
        self.assertIn("tickers.search", with_permissions.permissions)
        self.assertIn("tickers.prices", with_permissions.permissions)

        with_details = get_user_with_permission_details(authenticated_user.id)
        self.assertIsInstance(with_details, UserWithPermissionDetails)
        self.assertEqual(with_details.id, authenticated_user.id)
        detail_names = {p.name for p in with_details.permissions}
        self.assertIn("tickers.search", detail_names)
        self.assertIn("tickers.prices", detail_names)

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_service_layer_handles_missing_firebase_identity_gracefully(self) -> None:
        with self.assertRaises(UserNotFoundError) as ctx:
            get_authenticated_user("nonexistent-firebase-uid")
        self.assertIn("nonexistent-firebase-uid", str(ctx.exception))

    @unittest.skipUnless(_postgres_available(), "PostgreSQL user table is unavailable")
    def test_relational_permission_details_retrieved_correctly(self) -> None:
        self._setup_permissions()
        firebase_uid = uuid4().hex
        email = f"relational-{uuid4().hex}@example.com"
        self.addCleanup(self._cleanup_user, firebase_uid)

        created = create_user(self._make_create_request(email=email, password="test-pass", firebase_uid=firebase_uid))
        self._assign_permissions(created.id, ["tickers.search", "tickers.prices", "search.read"])

        response = get_user_with_permission_details(created.id)
        self.assertIsInstance(response, UserWithPermissionDetails)
        self.assertEqual(response.id, created.id)
        self.assertEqual(len(response.permissions), 3)

        names = {p.name for p in response.permissions}
        self.assertIn("tickers.search", names)
        self.assertIn("tickers.prices", names)
        self.assertIn("search.read", names)

        for p in response.permissions:
            self.assertIsInstance(p.id, int)
            self.assertIsInstance(p.name, str)
            self.assertIsInstance(p.description, (str, type(None)))

    def test_service_layer_has_no_http_dependencies(self) -> None:
        import ast
        import pathlib

        service_modules = [
            pathlib.Path("app/services/user_service.py"),
            pathlib.Path("app/services/exceptions.py"),
        ]

        http_imports = {"fastapi", "starlette", "uvicorn", "Request", "HTTPException", "Depends", "APIRouter"}

        for module_path in service_modules:
            if not module_path.exists():
                continue
            content = module_path.read_text()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and any(name in http_imports for name in [node.module] + [alias.name for alias in node.names]):
                        self.fail(f"Service module {module_path} imports HTTP-specific module: {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in http_imports:
                            self.fail(f"Service module {module_path} imports HTTP-specific module: {alias.name}")


if __name__ == "__main__":
    unittest.main()
