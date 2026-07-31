"""News endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_permission
from app.crud import get_ticker_news
from app.models import NewsRow

router = APIRouter(prefix="/tickers", tags=["news"])


@router.get("/{ticker}/news", response_model=list[NewsRow])
def get_news(
    ticker: str,
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    limit: int = Query(50, ge=1, le=200),
    permission: str = require_permission("tickers.news"),
) -> list[NewsRow]:
    return get_ticker_news(ticker, start, end, limit)
