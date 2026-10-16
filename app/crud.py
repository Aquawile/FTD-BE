"""Data-access layer: read-only CRUD functions against the PostgreSQL lakehouse schema."""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from app.db import query_dict, get_connection
import psycopg2.extras
from app.models import (
    AlertResponse,
    FilingElement,
    FilingSummary,
    FiscalYearEnd,
    NewsRow,
    PriceRow,
    SearchResult,
    TimelineEvent,
    TickerResult,
    TrackedTicker,
    WorkspaceResponse,
)

# `unified_staging` is now an always-empty view (WHERE false over
# unified_staging_archive). Live relational data lives in staging_finnhub
# (prices) and staging_gnews (news); this subquery unions them in the
# unified_staging column shape. SEC content is served from GCS.
_RELATIONAL_UNIFIED = """
    (
        SELECT target_ticker, target_cik, normalized_calendar_date, ingest_date,
               'finnhub' AS source, element_type, COALESCE(content_body, '') AS content_body,
               "current", change, NULL::text AS form_type, NULL::text AS item_number,
               NULL::text AS date_precision, NULL::text AS element_id
        FROM staging_finnhub
        UNION ALL
        SELECT target_ticker, target_cik, normalized_calendar_date, ingest_date,
               'gnews' AS source, element_type, COALESCE(content_body, '') AS content_body,
               NULL::numeric, NULL::numeric, NULL::text, NULL::text,
               NULL::text, NULL::text
        FROM staging_gnews
    ) u
"""

# Most recent quote per symbol from staging_finnhub (loaded daily from raw-data-strg/prices).
_LATEST_PRICES = """
    SELECT DISTINCT ON (target_ticker)
        target_ticker, "current", percent_change,
        COALESCE("timestamp", normalized_calendar_date) AS as_of
    FROM staging_finnhub
    WHERE "current" IS NOT NULL
    ORDER BY target_ticker, normalized_calendar_date DESC, ingest_date DESC NULLS LAST
"""


def search_tickers(
    query: str,
    limit: int = 20,
    sector: Optional[str] = None,
    sort_by: str = "ticker",
) -> list[TickerResult]:
    """
    Search tickers with optional sector filter and sorting.
    Returns tickers with sector.
    """
    # Build WHERE clause
    where_conditions = ["t.symbol ILIKE %s"]
    params = [f"%{query}%"]

    if sector and sector != "all":
        where_conditions.append("t.sector ILIKE %s")
        params.append(sector)

    where_clause = " AND ".join(where_conditions)

    # Determine sort order
    sort_map = {
        "ticker": "t.symbol",
        "hype": "t.evidence_score DESC",
        "evidence": "t.evidence_score DESC",
    }
    sort_column = sort_map.get(sort_by, "t.symbol")

    # cik is left blank: target_cik in the staging tables is misaligned for most
    # symbols; the correct CIK is resolved from GCS (vectorized_gcs) where needed.
    sql = f"""
        SELECT
            t.symbol AS ticker,
            ''::text AS cik,
            t.sector,
            t.evidence_score,
            NULL::text AS news_snippet
        FROM tickers t
        WHERE {where_clause}
        ORDER BY {sort_column}
        LIMIT %s
    """
    params.append(limit)
    rows = query_dict(sql, tuple(params))
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
            content_body,
            'gnews' AS source,
            url
        FROM staging_gnews
        WHERE target_ticker = %s
          AND normalized_calendar_date >= %s
          AND normalized_calendar_date <= %s
        ORDER BY normalized_calendar_date DESC, ingest_date DESC
        LIMIT %s
    """
    rows = query_dict(sql, (ticker, start, end, limit))
    return [NewsRow(**r) for r in rows]


def get_ticker_filings(ticker: str) -> list[FilingSummary]:
    # DEPRECATED: Use vectorized_gcs.list_filings_for_ticker instead
    from app.services.db_access_counter import increment_counter
    increment_counter("endpoint:ticker_filings")

    sql = """
        SELECT
            target_ticker,
            target_cik,
            form_type,
            accession_number,
            MIN(filing_date) AS filing_date,
            COUNT(*) AS element_count,
            CONCAT(
                'https://www.sec.gov/cgi-bin/browse-edgar?action=getfile&CIK=',
                target_cik,
                '&acckey=',
                REPLACE(accession_number, '-', '')
            ) AS url
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
    # DEPRECATED: Use vectorized_gcs.get_filing_elements_by_accession instead
    from app.services.db_access_counter import increment_counter
    increment_counter("endpoint:filing_elements")

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
    source_list = sources or ["finnhub", "gnews"]
    # SEC timeline data now served from vectorized GCS (ftd-vectorized-data bucket)
    # The "sec" source is no longer queried from PostgreSQL
    if "sec" in source_list:
        from app.services.db_access_counter import increment_counter
        increment_counter("endpoint:ticker_timeline")

    sql = f"""
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
        FROM {_RELATIONAL_UNIFIED}
        WHERE target_ticker = %s
          AND normalized_calendar_date >= %s
          AND normalized_calendar_date <= %s
          AND source = ANY(%s)
        ORDER BY normalized_calendar_date DESC
        LIMIT %s OFFSET %s
    """
    rows = query_dict(sql, (ticker, start, end, source_list, limit, offset))
    return [TimelineEvent(**r) for r in rows]


def get_ticker_fiscal_year_end(ticker: str) -> FiscalYearEnd | None:
    # DEPRECATED: Consider reading from vectorized GCS data instead
    from app.services.db_access_counter import increment_counter
    increment_counter("endpoint:fiscal_year_end")

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
    # DEPRECATED for SEC source: Use vectorized_gcs.search_vectorized_content instead
    if source is None or source == "sec":
        from app.services.db_access_counter import increment_counter
        increment_counter("endpoint:search_content")

    sql = f"""
        SELECT
            target_ticker,
            normalized_calendar_date,
            source,
            LEFT(content_body, 200) AS content_preview,
            element_id
        FROM {_RELATIONAL_UNIFIED}
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
    alerts_sql = "SELECT COUNT(*) AS count FROM alerts"

    articles_rows = query_dict(articles_sql)
    tickers_rows = query_dict(tickers_sql)
    alerts_rows = query_dict(alerts_sql)

    articles_count = articles_rows[0]["count"] if articles_rows else 0
    tickers_count = tickers_rows[0]["count"] if tickers_rows else 0
    alerts_count = alerts_rows[0]["count"] if alerts_rows else 0

    return {
        "articles_count": articles_count,
        "tickers_count": tickers_count,
        "alerts_count": alerts_count,
        "evidence_score": None,
    }


def get_tracked_tickers(limit: int = 500) -> list[TrackedTicker]:
    # Prefer the latest staging_finnhub quote over the tickers snapshot when it is newer,
    # so prices are current even if the snapshot columns haven't been refreshed.
    sql = f"""
        SELECT
            t.symbol, t.name, t.sector,
            CASE WHEN p.as_of > t.price_as_of OR t.price_as_of IS NULL
                 THEN COALESCE(p."current", t.current_price) ELSE t.current_price END AS current_price,
            t.evidence_score, t.hype_score,
            CASE WHEN p.as_of > t.price_as_of OR t.price_as_of IS NULL
                 THEN COALESCE(p.percent_change, t.change_percent) ELSE t.change_percent END AS change_percent,
            GREATEST(p.as_of, t.price_as_of) AS price_as_of
        FROM tickers t
        LEFT JOIN ({_LATEST_PRICES}) p ON p.target_ticker = t.symbol
        ORDER BY t.updated_at DESC
        LIMIT %s
    """
    rows = query_dict(sql, (limit,))
    results = []
    for r in rows:
        row = dict(r)
        if row.get("price_as_of") is not None:
            row["price_as_of"] = row["price_as_of"].isoformat()
        results.append(TrackedTicker(**row))
    return results


def get_user_workspaces(user_id: int) -> list[WorkspaceResponse]:
    sql = """
        SELECT w.id, w.name, w.created_at,
               COALESCE(ARRAY_AGG(wt.ticker_symbol) FILTER (WHERE wt.ticker_symbol IS NOT NULL), '{}') AS tickers
        FROM workspaces w
        LEFT JOIN workspace_tickers wt ON wt.workspace_id = w.id
        WHERE w.user_id = %s
        GROUP BY w.id, w.name, w.created_at
        ORDER BY w.created_at DESC
    """
    rows = query_dict(sql, (user_id,))
    results = []
    for r in rows:
        results.append(WorkspaceResponse(
            id=r["id"],
            name=r["name"],
            tickers=r["tickers"] or [],
            alerts=0,
            created_at=r["created_at"].isoformat() if r["created_at"] else None,
        ))
    return results


def create_workspace(user_id: int, name: str, ticker_symbols: list[str] | None = None) -> WorkspaceResponse:
    from app.db import execute
    tickers = ticker_symbols or []

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO workspaces (user_id, name, created_at) VALUES (%s, %s, NOW()) RETURNING id, name, created_at",
                (user_id, name),
            )
            ws = cur.fetchone()
            for symbol in tickers:
                cur.execute(
                    "INSERT INTO workspace_tickers (workspace_id, ticker_symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (ws["id"], symbol),
                )
        conn.commit()

    if not ws:
        raise RuntimeError("Failed to create workspace")

    workspace_id = ws["id"]
    return WorkspaceResponse(
        id=workspace_id,
        name=ws["name"],
        tickers=tickers,
        alerts=0,
        created_at=ws["created_at"].isoformat() if ws["created_at"] else None,
    )


def delete_workspace(user_id: int, workspace_id: int) -> None:
    from app.db import execute
    sql = """
        DELETE FROM workspaces
        WHERE id = %s AND user_id = %s
    """
    execute(sql, (workspace_id, user_id))


def add_ticker_to_workspace(workspace_id: int, ticker_symbol: str) -> None:
    from app.db import execute
    sql = """
        INSERT INTO workspace_tickers (workspace_id, ticker_symbol)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """
    execute(sql, (workspace_id, ticker_symbol))


def remove_ticker_from_workspace(workspace_id: int, ticker_symbol: str) -> None:
    from app.db import execute
    sql = """
        DELETE FROM workspace_tickers
        WHERE workspace_id = %s AND ticker_symbol = %s
    """
    execute(sql, (workspace_id, ticker_symbol))


def get_workspace_tickers(workspace_id: int) -> list[str]:
    sql = """
        SELECT ticker_symbol
        FROM workspace_tickers
        WHERE workspace_id = %s
        ORDER BY ticker_symbol
    """
    rows = query_dict(sql, (workspace_id,))
    return [r["ticker_symbol"] for r in rows]


def workspace_exists(workspace_id: int, user_id: int) -> bool:
    sql = "SELECT 1 FROM workspaces WHERE id = %s AND user_id = %s"
    rows = query_dict(sql, (workspace_id, user_id))
    return len(rows) > 0


def get_workspace_by_id(workspace_id: int, user_id: int):
    sql = """
        SELECT w.id, w.name, w.created_at,
               COALESCE(ARRAY_AGG(wt.ticker_symbol) FILTER (WHERE wt.ticker_symbol IS NOT NULL), '{}') AS tickers
        FROM workspaces w
        LEFT JOIN workspace_tickers wt ON wt.workspace_id = w.id
        WHERE w.id = %s AND w.user_id = %s
        GROUP BY w.id, w.name, w.created_at
    """
    rows = query_dict(sql, (workspace_id, user_id))
    if not rows:
        return None
    r = rows[0]
    return WorkspaceResponse(
        id=r["id"],
        name=r["name"],
        tickers=r["tickers"] or [],
        alerts=0,
        created_at=r["created_at"].isoformat() if r["created_at"] else None,
    )


def get_user_alerts(user_id: int, limit: int = 10) -> list[AlertResponse]:
    sql = """
        SELECT id, ticker, type, message, read, severity, created_at
        FROM alerts
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    rows = query_dict(sql, (user_id, limit))
    results = []
    for r in rows:
        results.append(AlertResponse(
            id=r["id"],
            ticker=r["ticker"],
            type=r["type"],
            message=r["message"],
            read=r["read"],
            severity=r["severity"],
            time=r["created_at"].isoformat() if r["created_at"] else None,
        ))
    return results


def get_all_alerts(limit: int = 10) -> list[AlertResponse]:
    sql = """
        SELECT id, ticker, type, message, read, severity, created_at
        FROM alerts
        ORDER BY created_at DESC
        LIMIT %s
    """
    rows = query_dict(sql, (limit,))
    results = []
    for r in rows:
        results.append(AlertResponse(
            id=r["id"],
            ticker=r["ticker"],
            type=r["type"],
            message=r["message"],
            read=r["read"],
            severity=r["severity"],
            time=r["created_at"].isoformat() if r["created_at"] else None,
        ))
    return results
