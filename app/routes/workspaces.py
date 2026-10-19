"""Workspace-related endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.crud import (
    add_ticker_to_workspace,
    archive_workspace,
    create_workspace,
    get_user_workspaces,
    get_workspace_by_id,
    get_workspace_tickers,
    remove_ticker_from_workspace,
    update_workspace,
    workspace_exists,
)
from app.models import WorkspaceResponse, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreateRequest(BaseModel):
    name: str
    ticker_symbols: list[str] | None = None


@router.get("", response_model=list[WorkspaceResponse])
def route_get_workspaces(
    current_user: User = Depends(get_current_application_user),
) -> list[WorkspaceResponse]:
    return get_user_workspaces(user_id=current_user.id)


@router.post("", response_model=WorkspaceResponse)
def route_create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_application_user),
) -> WorkspaceResponse:
    return create_workspace(user_id=current_user.id, name=payload.name, ticker_symbols=payload.ticker_symbols or [])


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def route_get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_application_user),
) -> WorkspaceResponse:
    ws = get_workspace_by_id(workspace_id=workspace_id, user_id=current_user.id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def route_update_workspace(
    workspace_id: int,
    change: WorkspaceUpdate,
    current_user: User = Depends(get_current_application_user),
) -> WorkspaceResponse:
    """Rename, set the description, or turn new-SEC-filing alerts on/off for the workspace's tickers."""
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    name = change.name.strip() if change.name is not None else None
    if name == "":
        raise HTTPException(status_code=422, detail="Workspace name can't be empty")
    update_workspace(current_user.id, workspace_id, name, change.description, change.alert_on_filings)
    return get_workspace_by_id(workspace_id=workspace_id, user_id=current_user.id)


@router.delete("/{workspace_id}")
def route_archive_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_application_user),
):
    """Archive: hidden from the list, kept in the database (data is never deleted)."""
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    archive_workspace(user_id=current_user.id, workspace_id=workspace_id)
    return {"status": "archived"}


@router.get("/{workspace_id}/tickers", response_model=list[str])
def route_get_workspace_tickers(
    workspace_id: int,
    current_user: User = Depends(get_current_application_user),
) -> list[str]:
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return get_workspace_tickers(workspace_id=workspace_id)


@router.post("/{workspace_id}/tickers")
def route_add_ticker(
    workspace_id: int,
    ticker_symbol: str = Body(..., embed=True),
    current_user: User = Depends(get_current_application_user),
):
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    try:
        add_ticker_to_workspace(workspace_id=workspace_id, ticker_symbol=ticker_symbol.strip().upper(), user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add ticker '{ticker_symbol}': possibly not a tracked ticker")
    return {"status": "added"}


@router.delete("/{workspace_id}/tickers/{ticker_symbol}")
def route_remove_ticker(
    workspace_id: int,
    ticker_symbol: str,
    current_user: User = Depends(get_current_application_user),
):
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    remove_ticker_from_workspace(workspace_id=workspace_id, ticker_symbol=ticker_symbol, user_id=current_user.id)
    return {"status": "removed"}
