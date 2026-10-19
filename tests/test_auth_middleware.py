from __future__ import annotations

import logging

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.auth.models import User
from app.services.exceptions import UserNotFoundError
from app.services.user_service import get_authenticated_user

client = TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
def test_missing_authorization_header_returns_401(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="app.auth.middleware"):
        response = client.get("/auth/me/user")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing Authorization header"}
    assert any("authentication_failed" in r.message and "reason=missing_authorization_header" in r.message for r in caplog.records)


@pytest.mark.unit
def test_invalid_authorization_header_format_returns_401(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="app.auth.middleware"):
        response = client.get("/auth/me/user", headers={"Authorization": "Token abc"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Authorization header format"}
    assert any("authentication_failed" in r.message and "reason=invalid_header_format" in r.message for r in caplog.records)


@pytest.mark.unit
def test_invalid_token_returns_401(monkeypatch, caplog) -> None:
    monkeypatch.setattr("app.auth.middleware.validate_firebase_token_with_reason", lambda token: (None, "invalid"))

    with caplog.at_level(logging.WARNING, logger="app.auth.middleware"):
        response = client.get("/auth/me/user", headers=_bearer("invalid-token"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert any("authentication_failed" in r.message and "reason=firebase_token_invalid" in r.message for r in caplog.records)


@pytest.mark.unit
def test_valid_firebase_token_without_application_user_creates_user(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token_with_reason",
        lambda token: ({"firebase_uid": "firebase-uid-123", "email": "user@example.com"}, None),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.get_authenticated_user",
        lambda uid: (_ for _ in ()).throw(UserNotFoundError("test")),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.synchronize_user",
        lambda identity: User(
            id=999,
            firebase_uid=identity["firebase_uid"],
            email=identity["email"],
            is_active=True,
            created_at="2026-08-09T00:00:00",
            updated_at="2026-08-09T00:00:00",
        ),
    )

    with caplog.at_level(logging.INFO, logger="app.auth.dependencies"):
        response = client.get("/auth/me/user", headers=_bearer("valid-token"))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": 999,
        "firebase_uid": "firebase-uid-123",
        "email": "user@example.com",
        "is_active": True,
        "created_at": "2026-08-09T00:00:00",
        "updated_at": "2026-08-09T00:00:00",
    }


@pytest.mark.unit
def test_synchronize_user_failure_returns_500(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token_with_reason",
        lambda token: ({"firebase_uid": "firebase-uid-123", "email": "user@example.com"}, None),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.get_authenticated_user",
        lambda uid: (_ for _ in ()).throw(UserNotFoundError("test")),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.synchronize_user",
        lambda identity: (_ for _ in ()).throw(RuntimeError("database connection lost")),
    )

    with caplog.at_level(logging.ERROR, logger="app.auth.dependencies"):
        response = client.get("/auth/me/user", headers=_bearer("valid-token"))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal server error"}
    assert any("authentication_sync_failed" in r.message for r in caplog.records)


@pytest.mark.unit
def test_valid_firebase_token_resolves_postgres_user(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token_with_reason",
        lambda token: ({"firebase_uid": "firebase-uid-456", "email": "user@example.com"}, None),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.get_authenticated_user",
        lambda uid: User(
            id=42,
            firebase_uid=uid,
            email="user@example.com",
            is_active=True,
            created_at="2026-08-04T00:00:00",
            updated_at="2026-08-04T00:00:00",
        ),
    )

    with caplog.at_level(logging.INFO, logger="app.auth.middleware"):
        response = client.get("/auth/me/user", headers=_bearer("valid-token"))
    assert response.status_code == 200
    assert response.json() == {
        "id": 42,
        "firebase_uid": "firebase-uid-456",
        "email": "user@example.com",
        "is_active": True,
        "created_at": "2026-08-04T00:00:00",
        "updated_at": "2026-08-04T00:00:00",
    }
    assert any("authentication_succeeded" in r.message and "method=firebase" in r.message for r in caplog.records)


@pytest.mark.unit
def test_database_failure_during_firebase_user_lookup_returns_500(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token_with_reason",
        lambda token: ({"firebase_uid": "firebase-uid-789", "email": "user@example.com"}, None),
    )
    monkeypatch.setattr(
        "app.auth.dependencies.get_authenticated_user",
        lambda uid: (_ for _ in ()).throw(RuntimeError("database connection lost")),
    )

    with caplog.at_level(logging.ERROR, logger="app.auth.dependencies"):
        response = client.get("/auth/me/user", headers=_bearer("valid-token"))
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert any("authentication_internal_error" in r.message and "reason=postgres_lookup_failed" in r.message for r in caplog.records)


@pytest.mark.unit
def test_non_firebase_token_is_rejected(monkeypatch) -> None:
    """Firebase is the only sign-in method: a token Firebase rejects gets 401 (no internal-JWT fallback)."""
    monkeypatch.setattr("app.auth.middleware.validate_firebase_token_with_reason", lambda token: (None, "invalid"))
    response = client.get("/auth/me/user", headers=_bearer("eyJhbGciOiJIUzI1NiJ9.old-internal-jwt.sig"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


@pytest.mark.unit
@pytest.mark.parametrize("method,path", [
    ("post", "/auth/login"), ("post", "/auth/register"), ("post", "/auth/users"),
    ("get", "/auth/users/1"), ("patch", "/auth/me/user"), ("delete", "/auth/me/user"),
])
def test_password_api_endpoints_are_gone(monkeypatch, method, path) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token_with_reason",
        lambda token: ({"firebase_uid": "uid", "email": "user@example.com"}, None),
    )
    response = getattr(client, method)(path, headers=_bearer("t"), **({"json": {}} if method in ("post", "patch") else {}))
    assert response.status_code in (404, 405)


@pytest.mark.unit
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_not_served(path) -> None:
    assert client.get(path).status_code in (401, 404)


@pytest.mark.unit
def test_expired_firebase_token_returns_401(monkeypatch, caplog) -> None:
    monkeypatch.setattr("app.auth.middleware.validate_firebase_token_with_reason", lambda token: (None, "expired"))

    with caplog.at_level(logging.WARNING, logger="app.auth.middleware"):
        response = client.get("/auth/me/user", headers=_bearer("expired-token"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert any("authentication_failed" in r.message and "reason=firebase_token_expired" in r.message for r in caplog.records)
