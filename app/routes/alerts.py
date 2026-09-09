"""Alert-related endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.crud import get_user_alerts
from app.models import AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def route_get_alerts(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_application_user),
) -> list[AlertResponse]:
    return get_user_alerts(user_id=current_user.id, limit=limit)
