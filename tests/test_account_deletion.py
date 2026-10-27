from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import crud
from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.main import app

pytestmark = pytest.mark.unit


def _conn():
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    ctx = MagicMock()
    ctx.__enter__.return_value = conn
    return ctx, conn, cur


def test_close_account_detaches_and_never_deletes_rows():
    ctx, conn, cur = _conn()
    with patch.object(crud, "get_connection", return_value=ctx):
        crud.close_user_account(7)
    sql = " ".join(c.args[0] for c in cur.execute.call_args_list)
    assert "DELETE" not in sql.upper() and "TRUNCATE" not in sql.upper()
    assert "archived_at" in sql and "alert_subscriptions SET active = FALSE" in sql
    assert "firebase_uid = NULL" in sql and "is_active = FALSE" in sql
    assert cur.execute.call_args_list[-1].args[1] == ("deleted-7@deleted.invalid", 7)
    conn.commit.assert_called_once()


def test_delete_me_closes_only_the_callers_account():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    user = User(id=7, firebase_uid="u", email="a@b.co", is_active=True, created_at=now, updated_at=now)
    app.dependency_overrides[get_current_application_user] = lambda: user
    try:
        with patch("app.routes.users.close_user_account") as close, patch(
            "app.auth.middleware.validate_firebase_token_with_reason",
            return_value=({"firebase_uid": "u", "email": "a@b.co", "email_verified": True}, None),
        ), patch("app.db.execute"):
            res = TestClient(app).delete("/users/me", headers={"Authorization": "Bearer x"})
    finally:
        app.dependency_overrides.pop(get_current_application_user, None)
    assert res.status_code == 200 and res.json() == {"closed": True}
    close.assert_called_once_with(7)
