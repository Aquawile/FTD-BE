from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.auth.models import User, UserPermissionsResponse, UserWithPermissionDetails, PermissionDetail
from app.services.exceptions import UserNotFoundError

client = TestClient(app)


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


if __name__ == "__main__":
    unittest.main()
