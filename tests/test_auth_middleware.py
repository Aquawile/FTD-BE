from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_authorization_header_returns_401() -> None:
    response = client.get("/auth/me/user")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing Authorization header"}


def test_invalid_authorization_header_format_returns_401() -> None:
    response = client.get("/auth/me/user", headers={"Authorization": "Token abc"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Authorization header format"}


def test_invalid_token_returns_401(monkeypatch) -> None:
    monkeypatch.setattr("app.auth.middleware.validate_firebase_token", lambda token: None)
    monkeypatch.setattr("app.auth.middleware.verify_token", lambda token: None)

    response = client.get("/auth/me/user", headers=_bearer("invalid-token"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_valid_firebase_token_without_application_user_returns_401(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token",
        lambda token: {"firebase_uid": "firebase-uid-123", "email": "user@example.com"},
    )
    monkeypatch.setattr("app.auth.middleware.get_user_by_firebase_uid", lambda uid: None)

    response = client.get("/auth/me/user", headers=_bearer("valid-token"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Authenticated Firebase identity has no associated application user"}


def test_valid_firebase_token_resolves_postgres_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.middleware.validate_firebase_token",
        lambda token: {"firebase_uid": "firebase-uid-456", "email": "user@example.com"},
    )
    monkeypatch.setattr(
        "app.auth.middleware.get_user_by_firebase_uid",
        lambda uid: {
            "id": 42,
            "firebase_uid": uid,
            "email": "user@example.com",
            "is_active": True,
            "created_at": "2026-08-04T00:00:00",
            "updated_at": "2026-08-04T00:00:00",
        },
    )

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
