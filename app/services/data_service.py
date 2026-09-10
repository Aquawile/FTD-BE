"""Application service layer for lakehouse data operations.

This module implements the application service layer that sits between the
HTTP request handlers and the PostgreSQL-backed data access layer. Services
accept application-level inputs, orchestrate data retrieval through the
repository layer, enforce application rules, and return typed domain results.

The service layer intentionally avoids HTTP concepts (Request objects, status
codes, headers, JSONResponse) so the same operations can be invoked from
FastAPI endpoints, background tasks, or direct test harnesses without
rewriting business logic.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Sequence

from app import crud
from app.models import (
    FilingElement,
    FilingSummary,
    FiscalYearEnd,
    NewsRow,
    PriceRow,
    SearchResult,
    TimelineEvent,
    TickerResult,
)
from app.services.exceptions import (
    DataRetrievalError,
    DataValidationError,
    FilingNotFoundError,
    TickerNotFoundError,
)

logger = logging.getLogger(__name__)

MAX_TICKER_LENGTH = 10
MAX_SEARCH_LIMIT = 200
DEFAULT_SEARCH_LIMIT = 20
MAX_NEWS_LIMIT = 500
DEFAULT_NEWS_LIMIT = 50
MAX_TIMELINE_LIMIT = 1000
DEFAULT_TIMELINE_LIMIT = 100
VALID_DATA_SOURCES = frozenset({"finnhub", "gnews", "sec"})


def _validate_ticker(ticker: str) -> str:
    """Validate and normalize a ticker symbol.

    Returns the uppercase ticker string. Raises DataValidationError for
    empty, whitespace-only, or excessively long tickers.
    """
    if not ticker or not ticker.strip():
        raise DataValidationError("Ticker symbol must not be empty")
    normalized = ticker.strip().upper()
    if len(normalized) > MAX_TICKER_LENGTH:
        raise DataValidationError(
            f"Ticker symbol must not exceed {MAX_TICKER_LENGTH} characters"
        )
    return normalized


def _validate_date_range(start: date, end: date) -> None:
    """Validate that start date is not after end date."""
    if start > end:
        raise DataValidationError("Start date must not be after end date")


def _validate_limit(limit: int, max_limit: int, default: int) -> int:
    """Clamp a request limit to a valid range."""
    if limit is None:
        return default
    if limit <= 0:
        return default
    return min(limit, max_limit)


def _validate_sources(sources: list[str] | None) -> list[str] | None:
    """Validate that requested data sources are recognized.

    Returns the validated list or None if no filtering is requested.
    Raises DataValidationError for unrecognized sources.
    """
    if sources is None:
        return None
    invalid = [s for s in sources if s not in VALID_DATA_SOURCES]
    if invalid:
        raise DataValidationError(
            f"Unrecognized data sources: {invalid}. Valid sources: {sorted(VALID_DATA_SOURCES)}"
        )
    return sources


def search_tickers(query: str, limit: int | None = None) -> list[TickerResult]:
    """Find tickers matching a search query.

    This service operation expresses the intent of discovering tickers by
    a partial symbol match. It validates the query, applies a reasonable
    result limit, and returns typed ticker results.

    Raises DataValidationError when the query is empty or invalid.
    Raises DataRetrievalError when the underlying database query fails.
    """
    if not query or not query.strip():
        raise DataValidationError("Search query must not be empty")
    normalized = query.strip().upper()
    clamped_limit = _validate_limit(limit, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT)
    logger.info("service:search_tickers query=%s limit=%s", normalized, clamped_limit)
    try:
        return crud.search_tickers(normalized, clamped_limit)
    except Exception as exc:
        logger.error("service:search_tickers failed query=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to search tickers: {exc}") from exc


def get_ticker_prices(
    ticker: str, start: date, end: date
) -> list[PriceRow]:
    """Retrieve historical price data for a ticker within a date range.

    This service operation expresses the intent of obtaining a ticker's
    price history. It validates the ticker symbol and date range, then
    delegates to the data access layer.

    Raises DataValidationError when inputs are invalid.
    Raises TickerNotFoundError when no price data exists for the ticker.
    Raises DataRetrievalError when the underlying database query fails.
    """
    normalized = _validate_ticker(ticker)
    _validate_date_range(start, end)
    logger.info("service:get_ticker_prices ticker=%s start=%s end=%s", normalized, start, end)
    try:
        results = crud.get_ticker_prices(normalized, start, end)
    except Exception as exc:
        logger.error("service:get_ticker_prices failed ticker=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve prices: {exc}") from exc
    if not results:
        raise TickerNotFoundError(
            f"No price data found for ticker {normalized} in the specified date range"
        )
    return results


def get_ticker_news(
    ticker: str,
    start: date,
    end: date,
    limit: int | None = None,
) -> list[NewsRow]:
    """Retrieve news articles for a ticker within a date range.

    This service operation expresses the intent of obtaining recent news
    coverage for a ticker. It validates inputs and applies a reasonable
    result limit.

    Raises DataValidationError when inputs are invalid.
    Raises TickerNotFoundError when no news exists for the ticker.
    Raises DataRetrievalError when the underlying database query fails.
    """
    normalized = _validate_ticker(ticker)
    _validate_date_range(start, end)
    clamped_limit = _validate_limit(limit, MAX_NEWS_LIMIT, DEFAULT_NEWS_LIMIT)
    logger.info("service:get_ticker_news ticker=%s start=%s end=%s limit=%s", normalized, start, end, clamped_limit)
    try:
        results = crud.get_ticker_news(normalized, start, end, clamped_limit)
    except Exception as exc:
        logger.error("service:get_ticker_news failed ticker=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve news: {exc}") from exc
    if not results:
        raise TickerNotFoundError(
            f"No news found for ticker {normalized} in the specified date range"
        )
    return results


def get_ticker_filings(ticker: str) -> list[FilingSummary]:
    """Retrieve filing summaries for a ticker.

    This service operation expresses the intent of obtaining an overview
    of SEC filings for a ticker, grouped by accession number with element counts.

    Raises DataValidationError when the ticker is invalid.
    Raises TickerNotFoundError when no filings exist for the ticker.
    Raises DataRetrievalError when the underlying database query fails.
    """
    normalized = _validate_ticker(ticker)
    logger.info("service:get_ticker_filings ticker=%s", normalized)
    try:
        results = crud.get_ticker_filings(normalized)
    except Exception as exc:
        logger.error("service:get_ticker_filings failed ticker=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve filings: {exc}") from exc
    if not results:
        raise TickerNotFoundError(f"No filings found for ticker {normalized}")
    return results


def get_filing_elements(
    accession_number: str,
    item_number: str | None = None,
    element_type: str | None = None,
) -> list[FilingElement]:
    """Retrieve individual elements within a specific SEC filing.

    This service operation expresses the intent of obtaining the detailed
    content elements of a filing, optionally filtered by item number or
    element type (quantitative/narrative).

    Raises DataValidationError when the accession number is invalid.
    Raises FilingNotFoundError when no elements exist for the filing.
    Raises DataRetrievalError when the underlying database query fails.
    """
    if not accession_number or not accession_number.strip():
        raise DataValidationError("Accession number must not be empty")
    normalized = accession_number.strip().upper()
    logger.info(
        "service:get_filing_elements accession=%s item=%s type=%s",
        normalized, item_number, element_type,
    )
    try:
        results = crud.get_filing_elements(normalized, item_number, element_type)
    except Exception as exc:
        logger.error("service:get_filing_elements failed accession=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve filing elements: {exc}") from exc
    if not results:
        raise FilingNotFoundError(
            f"No elements found for filing {normalized}"
        )
    return results


def get_ticker_timeline(
    ticker: str,
    start: date,
    end: date,
    sources: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TimelineEvent]:
    """Retrieve a unified timeline of events for a ticker.

    This service operation expresses the intent of assembling a chronological
    view of all data events (prices, news, filings) for a ticker. It resolves
    the relational data from multiple source tables into a single application-
    level result, so the client does not need to understand the underlying
    table structure or issue separate requests.

    Raises DataValidationError when inputs are invalid.
    Raises TickerNotFoundError when no timeline events exist.
    Raises DataRetrievalError when the underlying database query fails.
    """
    normalized = _validate_ticker(ticker)
    _validate_date_range(start, end)
    clamped_limit = _validate_limit(limit, MAX_TIMELINE_LIMIT, DEFAULT_TIMELINE_LIMIT)
    validated_sources = _validate_sources(sources)
    if offset < 0:
        offset = 0
    logger.info(
        "service:get_ticker_timeline ticker=%s start=%s end=%s sources=%s limit=%s offset=%s",
        normalized, start, end, validated_sources, clamped_limit, offset,
    )
    try:
        results = crud.get_ticker_timeline(
            normalized, start, end, validated_sources, clamped_limit, offset
        )
    except Exception as exc:
        logger.error("service:get_ticker_timeline failed ticker=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve timeline: {exc}") from exc
    if not results:
        raise TickerNotFoundError(
            f"No timeline events found for ticker {normalized} in the specified range"
        )
    return results


def get_ticker_fiscal_year_end(ticker: str) -> FiscalYearEnd:
    """Retrieve the fiscal year end date for a ticker.

    This service operation expresses the intent of obtaining a ticker's
    fiscal year boundary, which is useful for understanding reporting periods.
    It joins the fiscal_parameters table with staging_sec to resolve the
    ticker symbol to its CIK and then to its fiscal metadata.

    Raises DataValidationError when the ticker is invalid.
    Raises TickerNotFoundError when no fiscal year data exists.
    Raises DataRetrievalError when the underlying database query fails.
    """
    normalized = _validate_ticker(ticker)
    logger.info("service:get_ticker_fiscal_year_end ticker=%s", normalized)
    try:
        result = crud.get_ticker_fiscal_year_end(normalized)
    except Exception as exc:
        logger.error("service:get_ticker_fiscal_year_end failed ticker=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to retrieve fiscal year end: {exc}") from exc
    if result is None:
        raise TickerNotFoundError(
            f"No fiscal year end data found for ticker {normalized}"
        )
    return result


def search_content(
    keyword: str,
    source: str | None = None,
    limit: int | None = None,
) -> list[SearchResult]:
    """Search across all content for a keyword.

    This service operation expresses the intent of finding content matches
    across the unified data store. It validates the keyword and applies
    a reasonable result limit.

    Raises DataValidationError when the keyword is empty or source is invalid.
    Raises DataRetrievalError when the underlying database query fails.
    """
    if not keyword or not keyword.strip():
        raise DataValidationError("Search keyword must not be empty")
    normalized = keyword.strip()
    if source is not None and source not in VALID_DATA_SOURCES:
        raise DataValidationError(
            f"Unrecognized source: {source}. Valid sources: {sorted(VALID_DATA_SOURCES)}"
        )
    clamped_limit = _validate_limit(limit, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_LIMIT)
    logger.info("service:search_content keyword=%s source=%s limit=%s", normalized, source, clamped_limit)
    try:
        return crud.search_content(normalized, source, clamped_limit)
    except Exception as exc:
        logger.error("service:search_content failed keyword=%s error=%s", normalized, exc)
        raise DataRetrievalError(f"Failed to search content: {exc}") from exc


def get_dashboard_stats() -> dict:
    """Retrieve aggregated statistics for the dashboard.

    This service operation expresses the intent of obtaining high-level
    counts and metrics that summarize the data available in the system.
    It performs COUNT aggregations internally and returns application-level
    statistics without exposing raw database details.

    Raises DataRetrievalError when the underlying database query fails.
    """
    logger.info("service:get_dashboard_stats")
    try:
        return crud.get_dashboard_stats()
    except Exception as exc:
        logger.error("service:get_dashboard_stats failed error=%s", exc)
        raise DataRetrievalError(f"Failed to retrieve dashboard stats: {exc}") from exc
