"""User API boundary router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_application_user
from app.auth.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
def get_current_user_profile(
    current_user: User = Depends(get_current_application_user),
) -> User:
    return current_user
