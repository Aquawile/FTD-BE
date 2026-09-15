"""Workspace-related endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.crud import (
    add_ticker_to_workspace,
    create_workspace,
    delete_workspace,
    get_user_workspaces,
    get_workspace_by_id,
    get_workspace_tickers,
    remove_ticker_from_workspace,
    workspace_exists,
)
from app.models import WorkspaceResponse

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


@router.delete("/{workspace_id}")
def route_delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_application_user),
):
    if not workspace_exists(workspace_id=workspace_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    delete_workspace(user_id=current_user.id, workspace_id=workspace_id)
    return {"status": "deleted"}


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
        add_ticker_to_workspace(workspace_id=workspace_id, ticker_symbol=ticker_symbol)
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
    remove_ticker_from_workspace(workspace_id=workspace_id, ticker_symbol=ticker_symbol)
    return {"status": "removed"}
