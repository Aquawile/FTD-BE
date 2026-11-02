"""POST /auth/account-exists: public check used before sending a password-reset link."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit
client = TestClient(app)


def test_registered_email_is_reported_without_auth():
    with patch("app.auth.router.firebase_email_registered", return_value=True) as m:
        r = client.post("/auth/account-exists", json={"email": " a@b.com "})
    assert r.status_code == 200 and r.json() == {"registered": True}
    m.assert_called_once_with("a@b.com")


def test_unknown_email_is_not_registered():
    with patch("app.auth.router.firebase_email_registered", return_value=False):
        r = client.post("/auth/account-exists", json={"email": "x@y.com"})
    assert r.status_code == 200 and r.json() == {"registered": False}


def test_firebase_failure_is_503_not_false():
    with patch("app.auth.router.firebase_email_registered", side_effect=RuntimeError("no credentials")):
        r = client.post("/auth/account-exists", json={"email": "x@y.com"})
    assert r.status_code == 503


def test_missing_email_is_422():
    assert client.post("/auth/account-exists", json={}).status_code == 422
