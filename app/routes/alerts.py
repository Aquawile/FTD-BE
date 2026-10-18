"""Alert-related endpoints: a user's alerts and the subscriptions that produce them."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.crud import (
    create_user_subscription,
    get_user_alerts,
    get_user_subscription,
    get_user_subscriptions,
    mark_user_alerts_read,
    ticker_exists,
    update_user_subscription,
)
from app.models import (
    PRICE_ALERT_TYPES,
    AlertResponse,
    AlertSubscriptionCreate,
    AlertSubscriptionResponse,
    AlertSubscriptionUpdate,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def route_get_alerts(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_application_user),
) -> list[AlertResponse]:
    return get_user_alerts(user_id=current_user.id, limit=limit)


@router.post("/read")
def route_mark_alerts_read(
    alert_ids: list[int] | None = Body(default=None, embed=True),
    current_user: User = Depends(get_current_application_user),
) -> dict:
    """Mark the user's alerts read: all unread ones, or only alert_ids."""
    return {"updated": mark_user_alerts_read(current_user.id, alert_ids)}


@router.get("/subscriptions", response_model=list[AlertSubscriptionResponse])
def route_get_subscriptions(
    current_user: User = Depends(get_current_application_user),
) -> list[AlertSubscriptionResponse]:
    """The user's own subscriptions (active and paused). Empty if they have none."""
    return get_user_subscriptions(current_user.id)


@router.post("/subscriptions", response_model=AlertSubscriptionResponse, status_code=201)
def route_create_subscription(
    sub: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_application_user),
) -> AlertSubscriptionResponse:
    ticker = sub.ticker.strip().upper()
    if sub.alert_type in PRICE_ALERT_TYPES and sub.threshold is None:
        raise HTTPException(status_code=422, detail=f"{sub.alert_type} needs a threshold price")
    if sub.alert_type not in PRICE_ALERT_TYPES and sub.threshold is not None:
        raise HTTPException(status_code=422, detail=f"{sub.alert_type} does not take a threshold")
    if not ticker_exists(ticker):
        raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")
    new_id = create_user_subscription(current_user.id, ticker, sub.alert_type, sub.threshold)
    if new_id is None:
        raise HTTPException(status_code=409, detail=f"You already have a {sub.alert_type} subscription for {ticker}")
    return get_user_subscription(current_user.id, new_id)


@router.patch("/subscriptions/{subscription_id}", response_model=AlertSubscriptionResponse)
def route_update_subscription(
    subscription_id: int,
    change: AlertSubscriptionUpdate,
    current_user: User = Depends(get_current_application_user),
) -> AlertSubscriptionResponse:
    """Turn a subscription on/off or change its threshold. Subscriptions are never deleted."""
    existing = get_user_subscription(current_user.id, subscription_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if change.threshold is not None and existing.alert_type not in PRICE_ALERT_TYPES:
        raise HTTPException(status_code=422, detail=f"{existing.alert_type} does not take a threshold")
    update_user_subscription(current_user.id, subscription_id, change.active, change.threshold)
    return get_user_subscription(current_user.id, subscription_id)
