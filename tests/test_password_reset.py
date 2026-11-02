"""POST /auth/password-reset: a reset email goes only to active application users."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.unit
client = TestClient(app)
SERVICE = "app.services.user_service"


def test_registered_user_gets_email_without_auth():
    with patch(f"{SERVICE}.get_user_by_email", return_value={"id": 1, "is_active": True}), \
         patch(f"{SERVICE}.send_password_reset_email") as send:
        r = client.post("/auth/password-reset", json={"email": " A@B.com "})
    assert r.status_code == 200 and r.json() == {"sent": True}
    send.assert_called_once_with("a@b.com")


@pytest.mark.parametrize("row", [None, {"id": 2, "is_active": False}])
def test_unknown_or_inactive_is_not_sent_and_no_email(row):
    with patch(f"{SERVICE}.get_user_by_email", return_value=row), patch(f"{SERVICE}.send_password_reset_email") as send:
        r = client.post("/auth/password-reset", json={"email": "x@y.com"})
    assert r.status_code == 200 and r.json() == {"sent": False, "reason": "no_account"}
    send.assert_not_called()


def test_firebase_failure_is_503():
    with patch(f"{SERVICE}.get_user_by_email", return_value={"id": 1, "is_active": True}), \
         patch(f"{SERVICE}.send_password_reset_email", side_effect=OSError("down")):
        assert client.post("/auth/password-reset", json={"email": "a@b.com"}).status_code == 503


def test_missing_email_is_422():
    assert client.post("/auth/password-reset", json={}).status_code == 422
