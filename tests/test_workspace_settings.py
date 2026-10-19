"""Workspace settings routes: rename/description/filing alerts (PATCH) and archive (DELETE)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.main import app
from app.models import WorkspaceResponse

pytestmark = pytest.mark.unit

client = TestClient(app)
_USER = User(id=4, firebase_uid="uid", email="t@example.com", is_active=True,
             created_at="2026-01-01T00:00:00", updated_at="2026-01-01T00:00:00")
_H = {"Authorization": "Bearer t"}


@pytest.fixture(autouse=True)
def _auth():
    async def _fake(request=None) -> User:
        return _USER
    app.dependency_overrides[get_current_application_user] = _fake
    with patch("app.auth.middleware.validate_firebase_token_with_reason",
               return_value=({"firebase_uid": "uid", "email": "t@example.com"}, None)), patch("app.db.execute"):
        yield
    app.dependency_overrides.pop(get_current_application_user, None)


def _ws(**kw):
    return WorkspaceResponse(**{"id": 7, "name": "AI chips", "tickers": ["NVDA"], **kw})


def test_patch_saves_name_description_and_alerts():
    with patch("app.routes.workspaces.workspace_exists", return_value=True), \
         patch("app.routes.workspaces.update_workspace") as upd, \
         patch("app.routes.workspaces.get_workspace_by_id", return_value=_ws(name="Chips", alert_on_filings=True)):
        r = client.patch("/workspaces/7", headers=_H, json={"name": " Chips ", "description": "d", "alert_on_filings": True})
    assert r.status_code == 200 and r.json()["alert_on_filings"] is True
    upd.assert_called_once_with(4, 7, "Chips", "d", True)


def test_patch_rejects_blank_name():
    with patch("app.routes.workspaces.workspace_exists", return_value=True):
        assert client.patch("/workspaces/7", headers=_H, json={"name": "   "}).status_code == 422


def test_patch_other_users_workspace_404():
    with patch("app.routes.workspaces.workspace_exists", return_value=False), \
         patch("app.routes.workspaces.update_workspace") as upd:
        assert client.patch("/workspaces/9", headers=_H, json={"name": "x"}).status_code == 404
    upd.assert_not_called()


def test_delete_archives_instead_of_deleting():
    with patch("app.routes.workspaces.workspace_exists", return_value=True), \
         patch("app.routes.workspaces.archive_workspace") as arch:
        r = client.delete("/workspaces/7", headers=_H)
    assert r.json() == {"status": "archived"}
    arch.assert_called_once_with(user_id=4, workspace_id=7)
