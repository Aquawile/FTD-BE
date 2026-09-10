"""Ticker-related endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth.dependencies import get_current_application_user, require_permission
from app.auth.models import User
from app.crud import (
    get_ticker_filings,
    get_ticker_fiscal_year_end,
    get_ticker_news,
    get_ticker_prices,
    get_ticker_timeline,
    get_tracked_tickers,
    search_tickers,
)
from app.models import FiscalYearEnd, NewsRow, PriceRow, TimelineEvent, TickerResult, TrackedTicker

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("/tracked", response_model=list[TrackedTicker])
def route_get_tracked_tickers(
    limit: int = Query(500, ge=1, le=500),
    current_user: dict = Depends(get_current_application_user),
) -> list[TrackedTicker]:
    return get_tracked_tickers(limit=limit)


@router.get("/search", response_model=list[TickerResult])
def route_search_tickers(
    q: str = Query(..., min_length=1, description="Ticker symbol or partial match"),
    limit: int = Query(20, ge=1, le=100),
    sector: Optional[str] = Query(None, description="Filter by sector (e.g., semiconductors, ai, ev, cloud)"),
    sort_by: str = Query("ticker", description="Sort by: ticker, evidence, hype"),
    permission: str = require_permission("tickers.search"),
) -> list[TickerResult]:
    return search_tickers(q, limit, sector, sort_by)


@router.get("/{ticker}/prices", response_model=list[PriceRow])
def route_get_prices(
    ticker: str,
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    permission: str = require_permission("tickers.prices"),
) -> list[PriceRow]:
    return get_ticker_prices(ticker, start, end)


@router.get("/{ticker}/news", response_model=list[NewsRow])
def route_get_news(
    ticker: str,
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    limit: int = Query(50, ge=1, le=200),
    permission: str = require_permission("tickers.news"),
) -> list[NewsRow]:
    return get_ticker_news(ticker, start, end, limit)


class FilingSummaryResponse(BaseModel):
    target_ticker: str
    target_cik: str
    form_type: str
    accession_number: str
    filing_date: date | None = None
    element_count: int = 0


@router.get("/{ticker}/filings", response_model=list[FilingSummaryResponse])
def route_get_filings(
    ticker: str,
    start: Annotated[date | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    end: Annotated[date | None, Query(description="End date (YYYY-MM-DD)")] = None,
    form_type: Annotated[str | None, Query(description="Form type (e.g. 10-K, 8-K)")] = None,
    permission: str = require_permission("tickers.filings"),
) -> list[FilingSummaryResponse]:
    from app.crud import get_ticker_filings as _get_filings
    results = _get_filings(ticker)
    if start or end or form_type:
        filtered = []
        for r in results:
            if form_type and r.form_type != form_type:
                continue
            if r.filing_date:
                if start and r.filing_date < start:
                    continue
                if end and r.filing_date > end:
                    continue
            filtered.append(r)
        results = filtered
    return [FilingSummaryResponse(**r.model_dump()) for r in results]


@router.get("/{ticker}/timeline", response_model=list[TimelineEvent])
def route_get_timeline(
    ticker: str,
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    sources: str | None = Query(None, description="Comma-separated sources (finnhub,gnews,sec)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    permission: str = require_permission("tickers.timeline"),
) -> list[TimelineEvent]:
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
    return get_ticker_timeline(ticker, start, end, source_list, limit, offset)


@router.get("/{ticker}/fiscal-year-end", response_model=FiscalYearEnd)
def route_get_fiscal_year_end(
    ticker: str,
    permission: str = require_permission("tickers.fiscal_year_end"),
) -> FiscalYearEnd:
    result = get_ticker_fiscal_year_end(ticker)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Fiscal year end not found for ticker")
    return result
