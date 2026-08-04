from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.requests import Request

from app.auth.models import User
from app.auth.permissions import ALL_PERMISSIONS
from app.db import query_dict

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
    current_user = getattr(request.state, "current_user", None)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return current_user


async def get_current_permissions(user_id: int = Depends(get_current_user)) -> set[str]:
    rows = query_dict(
        "SELECT permission_name FROM user_permissions_index WHERE user_id = %s",
        (user_id,),
    )
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