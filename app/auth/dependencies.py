from __future__ import annotations

from typing import Annotated

import logging

from fastapi import Depends, HTTPException, status
from starlette.requests import Request

from app.auth.models import User
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.user_sync import synchronize_user
from app.services.exceptions import UserNotFoundError
from app.services.user_service import get_authenticated_user

logger = logging.getLogger(__name__)

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