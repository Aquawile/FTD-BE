"""Auth routes. Sign-in, sign-up, passwords and sessions live in Firebase
(project ftd-2026); the API only reads the signed-in user.

The old password-based endpoints (/auth/login, /auth/register, /auth/users,
PATCH/DELETE /auth/me/user) were removed on 2026-10-19: they created accounts
and tokens outside Firebase, and the web app never used them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from app.auth.dependencies import get_current_application_user
from app.auth.firebase_auth import validate_firebase_token
from app.auth.models import User, UserPermissionsResponse
from app.services.user_service import get_user_with_permissions

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def auth_me(request: Request):
    """Identity claims from the caller's Firebase ID token."""
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth_header[len("Bearer ") :]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    firebase_user = validate_firebase_token(token)
    if firebase_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return {
        "auth_method": "firebase",
        "firebase_uid": firebase_user.get("firebase_uid"),
        "email": firebase_user.get("email"),
        "email_verified": firebase_user.get("email_verified"),
    }


@router.get(
    "/me/user",
    response_model=User,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication", "model": None},
        status.HTTP_404_NOT_FOUND: {"description": "Application user not found", "model": None},
    },
)
def auth_me_user(current_user: User = Depends(get_current_application_user)) -> User:
    """The application user for the signed-in Firebase identity (created on first sign-in)."""
    return current_user


@router.get(
    "/me/user/permissions",
    response_model=UserPermissionsResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication", "model": None},
        status.HTTP_404_NOT_FOUND: {"description": "User not found", "model": None},
    },
)
def auth_me_user_permissions(
    current_user: User = Depends(get_current_application_user),
) -> UserPermissionsResponse:
    """The signed-in user with their granted permissions."""
    return get_user_with_permissions(current_user.id)
