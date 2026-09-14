"""Ticker-related endpoints."""

from __future__ import annotations

import logging
import os
import time
from datetime import date
from typing import Annotated, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
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
    url: str | None = None


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


_SECONDS_PER_HOUR = 3600
_SEC_CACHE_SECONDS = int(os.environ.get("SEC_CACHE_SECONDS", str(_SECONDS_PER_HOUR * 24)))
logger = logging.getLogger(__name__)


def _fetch_sec_content(sec_url: str) -> tuple[bytes, str]:
    """Fetch SEC.gov content with a compliant User-Agent.

    SEC requires a User-Agent that includes company/contact information.
    Returns (content, content_type).
    """
    import urllib.request
    import urllib.error

    headers = {
        "User-Agent": "FTD Research (research@ftd.com) Python/urllib",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    req = urllib.request.Request(sec_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "text/html")
            content = resp.read()
            return content, content_type
    except urllib.error.HTTPError as e:
        content = e.read()
        return content, "text/html"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error fetching SEC content: {e}")


def _get_sec_primary_doc(cik: str, accession_number: str) -> str | None:
    """Use the SEC data API to find the primary document name for a filing."""
    import json
    import urllib.request
    import urllib.error

    accession_dashes = accession_number.replace("-", "")
    cik_padded = cik.replace("-", "").zfill(10)
    api_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

    headers = {
        "User-Agent": "FTD Research (research@ftd.com) Python/urllib",
        "Accept": "application/json",
    }
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            recent = data.get("filings", {}).get("recent", {})
            accessions = recent.get("accessionNumber", [])
            forms = recent.get("form", [])
            docs = recent.get("primaryDocument", [])
            for i, acc in enumerate(accessions):
                if acc.replace("-", "") == accession_dashes:
                    return docs[i] if i < len(docs) else None
    except Exception:
        pass
    return accession_number + ".htm"


@router.get("/{ticker}/filings/{accession_number:path}/content")
def route_get_filing_content(
    ticker: str,
    accession_number: str,
    cik: str = Query(..., description="SEC CIK number for the filing"),
    _permission: str = require_permission("tickers.filings"),
) -> Response:
    """Proxy SEC filing content so the browser doesn't hit SEC's bot protection.

    SEC requires requests to include a contact-bearing User-Agent.  Browsers
    send their own UA which SEC blocks ("Undeclared Automated Tool").  This
    endpoint fetches the filing server-side with a compliant UA and returns
    the HTML to the caller.  For large filings (10-K, etc.) the content is
    fetched server-side so the browser doesn't deal with SEC's block pages.
    """
    if accession_number.endswith(".htm"):
        accession_number = accession_number[:-4]

    accession_no_dashes = accession_number.replace("-", "")
    cik_no_dashes = cik.replace("-", "")
    cik_padded = cik_no_dashes.zfill(10)

    primary_doc = _get_sec_primary_doc(cik, accession_no_dashes)

    sec_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_no_dashes}/{accession_no_dashes}/{primary_doc}"
    )

    logger.info("sec_proxy: ticker=%s accession=%s cik=%s doc=%s url=%s", ticker, accession_no_dashes, cik_no_dashes, primary_doc, sec_url)

    content, content_type = _fetch_sec_content(sec_url)

    return HTMLResponse(content=content, headers={
        "Content-Type": content_type,
        "Cache-Control": f"max-age={_SEC_CACHE_SECONDS}",
    })
