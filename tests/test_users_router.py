from __future__ import annotations

import os
import pytest
import unittest
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.auth.models import User, UserPermissionsResponse, UserWithPermissionDetails, PermissionDetail
from app.auth.hasher import hash_password
from app.db import _POOL, get_connection
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.auth.index_maintainer import sync_user_permissions_index

client = TestClient(app)


def _postgres_api_test_available() -> bool:
    try:
        os.environ.setdefault("PGHOST", "127.0.0.1")
        os.environ.setdefault("PGPORT", "5432")
        os.environ.setdefault("PGDATABASE", "ftd_lakehouse_api_test")
        os.environ.setdefault("PGUSER", "ftd_app")
        os.environ.setdefault("PGPASSWORD", "temp_password_123")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                row = cur.fetchone()
                if row[0] != "ftd_lakehouse_api_test":
                    return False
                cur.execute("SELECT to_regclass('public.users')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def _make_user(**overrides) -> User:
    defaults = {
        "id": 1,
        "firebase_uid": "test-firebase-uid",
        "email": "test@example.com",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    defaults.update(overrides)
    return User(**defaults)


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.api_contract
class TestUsersRouter(unittest.TestCase):
    def test_get_current_user_returns_user(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ):
            response = client.get("/users/me", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], user.id)
        self.assertEqual(data["email"], user.email)

    def test_get_current_user_permissions_returns_permissions(self) -> None:
        user = _make_user()
        permissions_response = UserPermissionsResponse(
            id=user.id,
            firebase_uid=user.firebase_uid,
            email=user.email,
            is_active=user.is_active,
            permissions=["tickers.search", "tickers.prices"],
        )
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permissions",
            return_value=permissions_response,
        ):
            response = client.get("/users/me/permissions", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["permissions"], ["tickers.search", "tickers.prices"])

    def test_get_current_user_permission_details_returns_details(self) -> None:
        user = _make_user()
        details_response = UserWithPermissionDetails(
            id=user.id,
            firebase_uid=user.firebase_uid,
            email=user.email,
            is_active=user.is_active,
            permissions=[
                PermissionDetail(id=1, name="tickers.search", description="Search tickers"),
                PermissionDetail(id=2, name="tickers.prices", description="Read prices"),
            ],
        )
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permission_details",
            return_value=details_response,
        ):
            response = client.get("/users/me/permission-details", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["permissions"]), 2)
        self.assertEqual(data["permissions"][0]["name"], "tickers.search")

    def test_get_current_user_permissions_handles_user_not_found(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permissions",
            side_effect=UserNotFoundError("User not found"),
        ):
            response = client.get("/users/me/permissions", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_current_user_permission_details_handles_user_not_found(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permission_details",
            side_effect=UserNotFoundError("User not found"),
        ):
            response = client.get("/users/me/permission-details", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_routes_require_authentication(self) -> None:
        response = client.get("/users/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.get("/users/me/permissions")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.get("/users/me/permission-details")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.db_integration
class TestUsersRouterPostgres(unittest.TestCase):
    """Layer Four API integration tests against ftd_lakehouse_api_test."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._api_test_db = "ftd_lakehouse_api_test"
        cls._pg_password = "temp_password_123"
        cls._test_firebase_uid = "test-firebase-uid-api"
        cls._test_email = "test-api@example.com"

        os.environ.setdefault("PGHOST", "127.0.0.1")
        os.environ.setdefault("PGPORT", "5432")
        os.environ.setdefault("PGDATABASE", cls._api_test_db)
        os.environ.setdefault("PGUSER", "ftd_app")
        os.environ.setdefault("PGPASSWORD", cls._pg_password)

        import app.db

        app.db._POOL = None

        cls._setup_test_data()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cleanup_test_data()
        os.environ.pop("PGHOST", None)
        os.environ.pop("PGPORT", None)
        os.environ.pop("PGDATABASE", None)
        os.environ.pop("PGUSER", None)
        os.environ.pop("PGPASSWORD", None)
        import app.db

        app.db._POOL = None

    @classmethod
    def _setup_test_data(cls) -> None:
        user_id = None
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
                    "INSERT INTO users (email, password_hash, firebase_uid, is_active) VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
                    (cls._test_email, hash_password("test-pass"), cls._test_firebase_uid, True),
                )
                cur.execute("SELECT id FROM users WHERE firebase_uid = %s", (cls._test_firebase_uid,))
                row = cur.fetchone()
                if row:
                    user_id = row[0]
                    cur.execute("SELECT id, name FROM permissions WHERE name = ANY(%s)", (["tickers.search", "tickers.prices"],))
                    perm_map = {row[1]: row[0] for row in cur.fetchall()}
                    for name in ["tickers.search", "tickers.prices"]:
                        perm_id = perm_map.get(name)
                        if perm_id is not None:
                            cur.execute(
                                "INSERT INTO user_permissions (user_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                (user_id, perm_id),
                            )
            conn.commit()

        if user_id is not None:
            sync_user_permissions_index(user_id)

    @classmethod
    def _cleanup_test_data(cls) -> None:
        try:
            with get_connection() as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE firebase_uid = %s", (cls._test_firebase_uid,))
                    row = cur.fetchone()
                    if row:
                        user_id = row[0]
                        cur.execute("DELETE FROM user_permissions WHERE user_id = %s", (user_id,))
                        cur.execute("DELETE FROM user_permissions_index WHERE user_id = %s", (user_id,))
                        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    cur.execute("DELETE FROM permissions WHERE name = ANY(%s)", (["tickers.search", "tickers.prices"],))
                conn.commit()
        except Exception:
            pass

    def test_get_current_user_from_postgres(self) -> None:
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": self._test_firebase_uid, "email": self._test_email}, None),
        ):
            response = client.get("/users/me", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["firebase_uid"], self._test_firebase_uid)
        self.assertEqual(data["email"], self._test_email)
        self.assertTrue(data["is_active"])

    def test_get_current_user_permissions_from_postgres(self) -> None:
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": self._test_firebase_uid, "email": self._test_email}, None),
        ):
            response = client.get("/users/me/permissions", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("tickers.search", data["permissions"])
        self.assertIn("tickers.prices", data["permissions"])

    def test_get_current_user_permission_details_from_postgres(self) -> None:
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": self._test_firebase_uid, "email": self._test_email}, None),
        ):
            response = client.get("/users/me/permission-details", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["permissions"]), 2)
        names = {p["name"] for p in data["permissions"]}
        self.assertIn("tickers.search", names)
        self.assertIn("tickers.prices", names)
        for p in data["permissions"]:
            self.assertIn(p["name"], {"tickers.search", "tickers.prices"})
            self.assertIsInstance(p["id"], int)
            self.assertIsInstance(p["description"], (str, type(None)))

    def test_authenticated_request_without_application_user_creates_user(self) -> None:
        unknown_firebase_uid = "unknown-firebase-uid"
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": unknown_firebase_uid, "email": "unknown@example.com"}, None),
        ):
            response = client.get("/users/me", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["firebase_uid"], unknown_firebase_uid)
        self.assertEqual(data["email"], "unknown@example.com")
        self.assertTrue(data["is_active"])

        from app.auth.repository import get_user_by_firebase_uid
        user = get_user_by_firebase_uid(unknown_firebase_uid)
        self.assertIsNotNone(user)
        self.addCleanup(self._cleanup_unknown_user)

    def _cleanup_unknown_user(self) -> None:
        from app.auth.repository import get_user_by_firebase_uid
        user = get_user_by_firebase_uid("unknown-firebase-uid")
        if user:
            import psycopg2
            from app.db import get_connection
            with get_connection() as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_permissions WHERE user_id = %s", (user["id"],))
                    cur.execute("DELETE FROM user_permissions_index WHERE user_id = %s", (user["id"],))
                    cur.execute("DELETE FROM users WHERE id = %s", (user["id"],))
                conn.commit()

    def test_missing_authorization_header_returns_401(self) -> None:
        response = client.get("/users/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.get("/users/me/permissions")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.get("/users/me/permission-details")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_request_body_returns_422(self) -> None:
        response = client.post(
            "/auth/login",
            json={"invalid": "payload"},
            headers={"Authorization": "Bearer valid-token"},
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_nonexistent_user_returns_404(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permissions",
            side_effect=UserNotFoundError("User not found"),
        ):
            response = client.get("/users/me/permissions", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_user_creation_returns_409(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.auth.router.create_user",
            side_effect=UserAlreadyExistsError("User with this email or Firebase identity already exists"),
        ):
            response = client.post(
                "/auth/users",
                json={"email": user.email, "password": "securepassword123"},
                headers={"Authorization": "Bearer valid-token"},
            )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_unexpected_internal_error_returns_500(self) -> None:
        user = _make_user()
        with patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": user.firebase_uid, "email": user.email}, None),
        ), patch(
            "app.auth.dependencies.get_authenticated_user",
            return_value=user,
        ), patch(
            "app.routes.users.get_user_with_permissions",
            side_effect=RuntimeError("Unexpected database failure"),
        ):
            failing_client = TestClient(app, raise_server_exceptions=False)
            response = failing_client.get("/users/me/permissions", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertEqual(data["detail"], "Internal server error")


if __name__ == "__main__":
    unittest.main()
