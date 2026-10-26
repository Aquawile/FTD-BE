import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.auth import dependencies as deps
from app.auth.models import User

pytestmark = pytest.mark.unit

CUTOFF = deps.EMAIL_VERIFICATION_REQUIRED_FROM


def _user(created):
    return User(id=1, firebase_uid="u", email="a@b.co", is_active=True, created_at=created, updated_at=created)


def _request(verified):
    return SimpleNamespace(state=SimpleNamespace(firebase_uid="u", email="a@b.co", email_verified=verified))


def _call(verified, created):
    with patch.object(deps, "get_authenticated_user", return_value=_user(created)):
        return asyncio.run(deps.get_current_application_user(_request(verified)))


def test_new_unverified_account_is_refused():
    with pytest.raises(HTTPException) as exc:
        _call(False, CUTOFF + timedelta(minutes=1))
    assert (exc.value.status_code, exc.value.detail) == (403, "email_not_verified")


def test_new_verified_account_is_allowed():
    assert _call(True, CUTOFF + timedelta(days=3)).id == 1


def test_account_created_before_the_cutoff_stays_allowed_unverified():
    assert _call(False, CUTOFF - timedelta(days=60)).id == 1
    assert _call(False, (CUTOFF - timedelta(days=1)).replace(tzinfo=None)).id == 1  # naive timestamps count as UTC


def test_missing_flag_is_not_treated_as_unverified():
    assert _call(None, datetime.now(timezone.utc)).id == 1
