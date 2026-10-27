import base64
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.main import app

pytestmark = pytest.mark.unit

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
GOOD = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()


@pytest.fixture
def client():
    now = datetime.now(timezone.utc)
    user = User(id=7, firebase_uid="u", email="a@b.co", is_active=True, created_at=now, updated_at=now)
    app.dependency_overrides[get_current_application_user] = lambda: user
    with patch("app.auth.middleware.validate_firebase_token_with_reason",
               return_value=({"firebase_uid": "u", "email": "a@b.co", "email_verified": True}, None)), \
         patch("app.db.execute"):
        yield TestClient(app)
    app.dependency_overrides.pop(get_current_application_user, None)


H = {"Authorization": "Bearer x"}


def test_save_and_read_back_own_photo(client):
    with patch("app.routes.users.set_user_avatar") as save, patch("app.routes.users.get_user_avatar", return_value=GOOD):
        assert client.put("/users/me/avatar", json={"avatar": GOOD}, headers=H).json() == {"saved": True}
        save.assert_called_once_with(7, GOOD)
        assert client.get("/users/me/avatar", headers=H).json() == {"avatar": GOOD}


@pytest.mark.parametrize("bad", [
    "data:image/png;base64," + base64.b64encode(JPEG).decode(),           # not a jpeg data url
    "data:image/jpeg;base64," + base64.b64encode(b"<script>x</script>").decode(),  # not jpeg bytes
    "data:image/jpeg;base64,!!!not base64!!!",
    "data:image/jpeg;base64," + "A" * 130_000,                            # too large
    "https://example.com/me.jpg",
])
def test_bad_photos_are_refused_and_nothing_is_saved(client, bad):
    with patch("app.routes.users.set_user_avatar") as save:
        assert client.put("/users/me/avatar", json={"avatar": bad}, headers=H).status_code == 422
        save.assert_not_called()


def test_photo_endpoints_need_sign_in():
    c = TestClient(app)
    assert c.get("/users/me/avatar").status_code == 401
    assert c.put("/users/me/avatar", json={"avatar": GOOD}).status_code == 401
