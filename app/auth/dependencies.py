from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import logging
import os

from fastapi import Depends, HTTPException, status
from starlette.requests import Request

from app.auth.models import User
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.user_sync import synchronize_user
from app.services.exceptions import UserNotFoundError
from app.services.user_service import get_authenticated_user

logger = logging.getLogger(__name__)

# Accounts created on or after this moment must verify their email before using the API.
# Accounts that already existed are not asked to (they never were). Override with the env var.
EMAIL_VERIFICATION_REQUIRED_FROM = datetime.fromisoformat(
    os.environ.get("EMAIL_VERIFICATION_REQUIRED_FROM", "2026-10-26T21:30:00+00:00")
)


def _must_verify_email(request: Request, user: User) -> bool:
    # Only an explicit "not verified" from the Firebase token counts; real tokens always carry the flag.
    if getattr(request.state, "email_verified", None) is not False:
        return False
    created = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=timezone.utc)
    return created >= EMAIL_VERIFICATION_REQUIRED_FROM


async def get_current_application_user(request: Request) -> User:
    firebase_uid = getattr(request.state, "firebase_uid", None)
    if firebase_uid is not None:
        try:
            user = get_authenticated_user(firebase_uid)
        except UserNotFoundError:
            email = getattr(request.state, "email", "")
            try:
                user = synchronize_user({"firebase_uid": firebase_uid, "email": email})
            except Exception:
                logger.error("authentication_sync_failed: reason=user_creation_failed firebase_uid=%s", firebase_uid, exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error",
                )
        except Exception:
            logger.error("authentication_internal_error: reason=postgres_lookup_failed firebase_uid=%s", firebase_uid, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
        if _must_verify_email(request, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_permissions(current_user: User = Depends(get_current_application_user)) -> set[str]:
    from app.services.user_service import get_user_permissions
    rows = get_user_permissions(current_user.id)
    if not rows:
        from app.auth.user_sync import ensure_default_permissions
        try:
            if ensure_default_permissions(current_user.id):
                rows = get_user_permissions(current_user.id)
        except Exception:
            logger.error("permission_heal_failed: user_id=%s", current_user.id, exc_info=True)
    return {row["permission_name"] for row in rows}


def require_permission(permission: str):
    async def _require_permission(
        permissions: set[str] = Depends(get_current_permissions),
    ) -> set[str]:
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: required '{permission}'",
            )
        return permissions

    return Depends(_require_permission)