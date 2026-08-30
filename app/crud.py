"""Data-access layer: read-only CRUD functions against the PostgreSQL lakehouse schema."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.db import query_dict
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


def search_tickers(query: str, limit: int = 20) -> list[TickerResult]:
    sql = """
        SELECT DISTINCT target_ticker AS ticker, target_cik AS cik
        FROM unified_staging
        WHERE target_ticker ILIKE %s
        ORDER BY target_ticker
        LIMIT %s
    """
    rows = query_dict(sql, (f"%{query}%", limit))
    return [TickerResult(**r) for r in rows]


def get_ticker_prices(
    ticker: str, start: date, end: date
) -> list[PriceRow]:
    sql = """
        SELECT
            normalized_calendar_date,
            current,
            change,
            percent_change,
            open,
            high,
            low,
            previous_close
        FROM staging_finnhub
        WHERE target_ticker = %s
          AND normalized_calendar_date >= %s
          AND normalized_calendar_date <= %s
        ORDER BY normalized_calendar_date
    """
    rows = query_dict(sql, (ticker, start, end))
    return [PriceRow(**r) for r in rows]


def get_ticker_news(
    ticker: str,
    start: date,
    end: date,
    limit: int = 50,
) -> list[NewsRow]:
    sql = """
        SELECT
            target_ticker,
            normalized_calendar_date,
            ingest_date,
            content_body
        FROM staging_gnews
        WHERE target_ticker = %s
          AND normalized_calendar_date >= %s
          AND normalized_calendar_date <= %s
        ORDER BY ingest_date DESC
        LIMIT %s
    """
    rows = query_dict(sql, (ticker, start, end, limit))
    return [NewsRow(**r) for r in rows]


def get_ticker_filings(ticker: str) -> list[FilingSummary]:
    sql = """
        SELECT
            target_ticker,
            target_cik,
            form_type,
            accession_number,
            MIN(filing_date) AS filing_date,
            COUNT(*) AS element_count
        FROM staging_sec
        WHERE target_ticker = %s
        GROUP BY target_ticker, target_cik, form_type, accession_number
        ORDER BY filing_date DESC
    """
    rows = query_dict(sql, (ticker,))
    return [FilingSummary(**r) for r in rows]


def get_filing_elements(
    accession_number: str,
    item_number: str | None = None,
    element_type: str | None = None,
) -> list[FilingElement]:
    sql = """
        SELECT
            element_id,
            accession_number,
            item_number,
            content_type,
            element_type,
            content_body,
            raw_text_string,
            NULLIF(period_of_report, '') AS period_of_report,
            filing_date,
            date_precision
        FROM staging_sec
        WHERE accession_number = %s
          AND item_number = COALESCE(%s, item_number)
          AND element_type = COALESCE(%s, element_type)
        ORDER BY item_number, element_id
    """
    rows = query_dict(sql, (accession_number, item_number, element_type))
    return [FilingElement(**r) for r in rows]


def get_ticker_timeline(
    ticker: str,
    start: date,
    end: date,
    sources: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[TimelineEvent]:
    sql = """
        SELECT
            normalized_calendar_date,
            source,
            element_type,
            content_body,
            current,
            change,
            form_type,
            item_number,
            date_precision
        FROM unified_staging
        WHERE target_ticker = %s
          AND normalized_calendar_date >= %s
          AND normalized_calendar_date <= %s
          AND source = ANY(%s)
        ORDER BY normalized_calendar_date DESC
        LIMIT %s OFFSET %s
    """
    source_list = sources or ["finnhub", "gnews", "sec"]
    rows = query_dict(sql, (ticker, start, end, source_list, limit, offset))
    return [TimelineEvent(**r) for r in rows]


def get_ticker_fiscal_year_end(ticker: str) -> FiscalYearEnd | None:
    sql = """
        SELECT
            s.target_ticker,
            s.target_cik,
            f.fiscal_year_end_date,
            f.source_accession
        FROM fiscal_parameters f
        JOIN staging_sec s ON s.target_cik = f.target_cik
        WHERE s.target_ticker = %s
        LIMIT 1
    """
    rows = query_dict(sql, (ticker,))
    if not rows:
        return None
    return FiscalYearEnd(**rows[0])


def search_content(
    keyword: str,
    source: str | None = None,
    limit: int = 50,
) -> list[SearchResult]:
    sql = """
        SELECT
            target_ticker,
            normalized_calendar_date,
            source,
            LEFT(content_body, 200) AS content_preview,
            element_id
        FROM unified_staging
        WHERE content_body ILIKE %s
          AND source = COALESCE(%s, source)
        ORDER BY normalized_calendar_date DESC
        LIMIT %s
    """
    rows = query_dict(sql, (f"%{keyword}%", source, limit))
    return [SearchResult(**r) for r in rows]


def get_dashboard_stats() -> dict:
    articles_sql = "SELECT COUNT(*) AS count FROM unified_staging"
    tickers_sql = "SELECT COUNT(DISTINCT target_ticker) AS count FROM unified_staging WHERE target_ticker IS NOT NULL AND target_ticker <> ''"

    articles_rows = query_dict(articles_sql)
    tickers_rows = query_dict(tickers_sql)

    articles_count = articles_rows[0]["count"] if articles_rows else 0
    tickers_count = tickers_rows[0]["count"] if tickers_rows else 0

    return {
        "articles_count": articles_count,
        "tickers_count": tickers_count,
        "alerts_count": 0,
        "evidence_score": None,
    }
