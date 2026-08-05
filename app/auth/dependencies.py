from __future__ import annotations

from typing import Annotated

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.requests import Request

from app.auth.models import User
from app.auth.permissions import ALL_PERMISSIONS
from app.services.user_service import get_authenticated_user, get_authenticated_user_by_id

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    from app.auth.token import verify_token

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    email = payload.get("email")
    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )
    return {"user_id": int(user_id), "email": email}


async def get_current_application_user(request: Request) -> User:
    firebase_uid = getattr(request.state, "firebase_uid", None)
    user_id = getattr(request.state, "user_id", None)
    if firebase_uid is not None:
        try:
            user = get_authenticated_user(firebase_uid)
        except Exception:
            logger.error("authentication_internal_error: reason=postgres_lookup_failed firebase_uid=%s", firebase_uid, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
        if user is None:
            logger.warning("authentication_failed: reason=postgres_user_not_found firebase_uid=%s", firebase_uid)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated Firebase identity has no associated application user",
            )
        return user
    if user_id is not None:
        try:
            user = get_authenticated_user_by_id(user_id)
        except Exception:
            logger.error("authentication_internal_error: reason=postgres_lookup_failed user_id=%s", user_id, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
        if user is None:
            logger.warning("authentication_failed: reason=postgres_user_not_found user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated token has no associated application user",
            )
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_current_permissions(user_id: int = Depends(get_current_user)) -> set[str]:
    from app.services.user_service import get_user_permissions
    rows = get_user_permissions(user_id)
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