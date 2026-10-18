"""Ticker-related endpoints."""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.auth.dependencies import get_current_application_user, require_permission
from app.crud import (
    get_ticker_news,
    get_ticker_news_bounds,
    get_ticker_prices,
    get_tracked_tickers,
    search_tickers,
)
from app.models import NewsRow, PriceRow, PriceTimeline, TimelineEvent, TickerResult, TrackedTicker, FiscalYearEnd

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("/tracked", response_model=list[TrackedTicker])
def route_get_tracked_tickers(
    limit: int = Query(500, ge=1, le=500),
    symbol: str | None = Query(None, min_length=1, max_length=10, description="Return only this ticker"),
) -> list[TrackedTicker]:
    return get_tracked_tickers(limit=limit, symbol=symbol.strip().upper() if symbol else None)


@router.get("/search", response_model=list[TickerResult])
def route_search_tickers(
    q: str = Query(..., min_length=1, description="Ticker symbol or partial match"),
    limit: int = Query(20, ge=1, le=100),
    sector: Optional[str] = Query(None, description="Filter by sector (e.g., semiconductors, ai, ev, cloud)"),
    sort_by: str = Query("ticker", description="Sort by: ticker"),
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


@router.get("/{ticker}/price-timeline", response_model=PriceTimeline)
def route_get_price_timeline(
    ticker: str,
    window_days: int = Query(365, ge=30, le=365, description="Window length in calendar days"),
    permission: str = require_permission("tickers.prices"),
) -> PriceTimeline:
    """Daily close series on a fixed calendar window, filled only where finnhub data exists."""
    from app.services.price_timeline import build_price_timeline

    return build_price_timeline(ticker, window_days)


@router.get("/{ticker}/news", response_model=list[NewsRow])
def route_get_news(
    ticker: str,
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, description="Rows to skip (page * limit)"),
    permission: str = require_permission("tickers.news"),
) -> list[NewsRow]:
    """One page of news, most recent first.

    Headers: X-Total-Count = articles in [start, end]; X-Earliest-Date = the
    ticker's oldest article, so the UI can page from any start date to today.
    """
    rows = get_ticker_news(ticker, start, end, limit, offset)
    total, earliest = get_ticker_news_bounds(ticker, start, end)
    response.headers["X-Total-Count"] = str(total)
    if earliest is not None:
        response.headers["X-Earliest-Date"] = earliest.isoformat()
    return rows


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
    from app.services.vectorized_gcs import list_filings_for_ticker

    raw_results = list_filings_for_ticker(ticker)

    if start or end or form_type:
        filtered = []
        for r in raw_results:
            if form_type and r.form_type != form_type:
                continue
            if r.filing_date:
                if start and r.filing_date < start:
                    continue
                if end and r.filing_date > end:
                    continue
            filtered.append(r)
        raw_results = filtered

    return [FilingSummaryResponse(**r.model_dump()) for r in raw_results]


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

    from app.services.vectorized_gcs import get_timeline_from_gcs
    from app.crud import get_ticker_timeline as _get_ticker_timeline

    timeline_events: list[TimelineEvent] = []

    if source_list and "sec" in source_list:
        sec_sources = [s for s in source_list if s != "sec"]
        if sec_sources:
            timeline_events.extend(_get_ticker_timeline(ticker, start, end, sec_sources, limit, offset))
        timeline_events.extend(get_timeline_from_gcs(ticker, start, end, limit, offset))
        timeline_events.sort(key=lambda x: x.normalized_calendar_date or date.min, reverse=True)
        timeline_events = timeline_events[:limit]
    else:
        timeline_events = _get_ticker_timeline(ticker, start, end, source_list, limit, offset)
        if source_list is None:
            timeline_events.extend(get_timeline_from_gcs(ticker, start, end, limit, offset))

    return timeline_events


@router.get("/{ticker}/fiscal-year-end", response_model=FiscalYearEnd)
def route_get_fiscal_year_end(
    ticker: str,
    permission: str = require_permission("tickers.fiscal_year_end"),
) -> FiscalYearEnd:
    from app.services.vectorized_gcs import get_fiscal_year_end_from_gcs
    result = get_fiscal_year_end_from_gcs(ticker)
    if result is None:
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
    """Use the SEC data API to find the primary document name for a filing.

    This is a fallback for filings not found in raw-data-strg GCS bucket.
    """
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
    return None


@router.get("/{ticker}/filings/{accession_number:path}/content")
def route_get_filing_content(
    ticker: str,
    accession_number: str,
    cik: str = Query(..., description="SEC CIK number for the filing"),
    request: Request = None,
) -> Response:
    """Serve SEC filing content from raw-data-strg (GCS) with SEC.gov fallback.

    Tries GCS first for speed and to avoid SEC rate limits. Falls back to
    SEC.gov if the filing is not in GCS.
    """
    import time as _time
    _audit_start = _time.time()

    if accession_number.endswith(".htm"):
        accession_number = accession_number[:-4]

    accession_no_dashes = accession_number.replace("-", "")
    accession_with_dashes = accession_no_dashes
    if len(accession_with_dashes) == 18:
        accession_with_dashes = f"{accession_with_dashes[:10]}-{accession_with_dashes[10:12]}-{accession_with_dashes[12:]}"
    cik_no_dashes = cik.replace("-", "")
    cik_padded = cik_no_dashes.zfill(10)

    from app.services.vectorized_gcs import get_filing_content_from_gcs

    content, content_type, found_in_gcs = get_filing_content_from_gcs(ticker, accession_no_dashes, cik_padded)

    _audit_ms = int((_time.time() - _audit_start) * 1000)

    if found_in_gcs:
        from app.services.audit import log_sec_content_proxy
        log_sec_content_proxy(
            request=request,
            endpoint=f"/api/tickers/{ticker}/filings/{accession_no_dashes}/content",
            status=200,
            duration_ms=_audit_ms,
            details={
                "ticker": ticker,
                "accession_number": accession_no_dashes,
                "cik": cik_no_dashes,
                "source": "gcs",
                "content_length": len(content),
            },
        )
        return HTMLResponse(content=content, headers={
            "Content-Type": content_type,
            "Cache-Control": f"max-age={_SEC_CACHE_SECONDS}",
        })

    primary_doc = _get_sec_primary_doc(cik, accession_no_dashes)

    if primary_doc is not None:
        sec_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_no_dashes}/{accession_no_dashes}/{primary_doc}"
        )
    else:
        sec_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getfile&CIK={cik_padded}&acckey={accession_with_dashes}"
        )

    content, content_type = _fetch_sec_content(sec_url)

    _audit_ms = int((_time.time() - _audit_start) * 1000)
    from app.services.audit import log_sec_content_proxy
    log_sec_content_proxy(
        request=request,
        endpoint=f"/api/tickers/{ticker}/filings/{accession_no_dashes}/content",
        status=200,
        duration_ms=_audit_ms,
        details={
            "ticker": ticker,
            "accession_number": accession_no_dashes,
            "cik": cik_no_dashes,
            "source": "secgov",
            "content_length": len(content),
        },
    )

    return HTMLResponse(content=content, headers={
        "Content-Type": content_type,
        "Cache-Control": f"max-age={_SEC_CACHE_SECONDS}",
    })
