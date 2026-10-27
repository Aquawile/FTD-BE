from uuid import uuid4

import pytest

from app import crud
from app.auth.user_sync import synchronize_user
from app.db import get_connection

pytestmark = pytest.mark.db_integration

PHOTO = "data:image/jpeg;base64,/9j/4AAQ"


def test_photo_is_stored_on_the_users_row_and_replaced_not_duplicated():
    uid = uuid4().hex
    user = synchronize_user({"firebase_uid": uid, "email": f"avatar.{uid[:8]}@example.com"})
    try:
        assert crud.get_user_avatar(user.id) is None
        crud.set_user_avatar(user.id, PHOTO)
        assert crud.get_user_avatar(user.id) == PHOTO
        crud.set_user_avatar(user.id, PHOTO + "AAAA")
        assert crud.get_user_avatar(user.id) == PHOTO + "AAAA"
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE firebase_uid = %s", (uid,))
            conn.commit()
