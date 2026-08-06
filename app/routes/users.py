"""User API boundary router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_application_user
from app.auth.models import User, UserPermissionsResponse, UserWithPermissionDetails
from app.services.exceptions import UserNotFoundError
from app.services.user_service import (
    get_user_with_permission_details,
    get_user_with_permissions,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
def get_current_user_profile(
    current_user: User = Depends(get_current_application_user),
) -> User:
    return current_user


@router.get("/me/permissions", response_model=UserPermissionsResponse)
def get_current_user_permissions(
    current_user: User = Depends(get_current_application_user),
) -> UserPermissionsResponse:
    try:
        return get_user_with_permissions(current_user.id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.get("/me/permission-details", response_model=UserWithPermissionDetails)
def get_current_user_permission_details(
    current_user: User = Depends(get_current_application_user),
) -> UserWithPermissionDetails:
    try:
        return get_user_with_permission_details(current_user.id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
