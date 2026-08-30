"""Dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.crud import get_dashboard_stats
from app.models import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def route_dashboard_stats(
    permission: str = require_permission("dashboard.read"),
) -> DashboardStats:
    stats = get_dashboard_stats()
    return DashboardStats(**stats)
