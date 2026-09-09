"""Workspace-related endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.crud import get_user_workspaces
from app.models import WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def route_get_workspaces(
    current_user: User = Depends(get_current_application_user),
) -> list[WorkspaceResponse]:
    return get_user_workspaces(user_id=current_user.id)
