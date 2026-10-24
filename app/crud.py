"""Data-access layer: read-only CRUD functions against the PostgreSQL lakehouse schema."""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from app.db import query_dict, get_connection
import psycopg2.extras
from app.models import (
    AlertResponse,
    AlertSummary,
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

# Name shown under a ticker: tickers.name when it is a real name (most rows just
# repeat the symbol), else the 10-K company name (ticker_company_names), else the symbol.
_DISPLAY_NAME = "COALESCE(NULLIF(t.name, t.symbol), n.company_name, t.symbol)"
_COMPANY_NAMES_JOIN = "LEFT JOIN ticker_company_names n ON n.symbol = t.symbol"

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
    # Match the symbol or the company name ("apple" finds AAPL).
    where_conditions = [f"(t.symbol ILIKE %s OR {_DISPLAY_NAME} ILIKE %s)"]
    params = [f"%{query}%", f"%{query}%"]

    if sector and sector != "all":
        where_conditions.append("t.sector ILIKE %s")
        params.append(sector)

    where_clause = " AND ".join(where_conditions)

    # Determine sort order
    sort_map = {
        "ticker": "t.symbol",
    }
    sort_column = sort_map.get(sort_by, "t.symbol")

    # cik is left blank: target_cik in the staging tables is misaligned for most
    # symbols; the correct CIK is resolved from GCS (vectorized_gcs) where needed.
    sql = f"""
        SELECT
            t.symbol AS ticker,
            {_DISPLAY_NAME} AS name,
            ''::text AS cik,
            t.sector,
            NULL::text AS news_snippet
        FROM tickers t
        {_COMPANY_NAMES_JOIN}
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
    # One row per day: the newest ingest wins if a day was loaded more than once.
    sql = """
        SELECT DISTINCT ON (normalized_calendar_date)
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
        ORDER BY normalized_calendar_date, ingest_date DESC NULLS LAST
    """
    rows = query_dict(sql, (ticker, start, end))
    return [PriceRow(**r) for r in rows]


def get_ticker_news(
    ticker: str,
    start: date,
    end: date,
    limit: int = 50,
    offset: int = 0,
) -> list[NewsRow]:
    # Fully ordered (ctid breaks ties) so offset paging never repeats or skips rows.
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
        ORDER BY normalized_calendar_date DESC, ingest_date DESC, ctid DESC
        LIMIT %s OFFSET %s
    """
    rows = query_dict(sql, (ticker, start, end, limit, offset))
    return [NewsRow(**r) for r in rows]


def get_ticker_news_bounds(ticker: str, start: date, end: date) -> tuple[int, date | None]:
    """(articles in [start, end], earliest article date for the ticker) for paging."""
    rows = query_dict(
        """
        SELECT
            COUNT(*) FILTER (WHERE normalized_calendar_date >= %s AND normalized_calendar_date <= %s) AS total,
            MIN(normalized_calendar_date)::date AS earliest
        FROM staging_gnews
        WHERE target_ticker = %s
        """,
        (start, end, ticker),
    )
    if not rows:
        return 0, None
    return int(rows[0]["total"] or 0), rows[0]["earliest"]


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
    }


def get_tracked_tickers(limit: int = 500, symbol: str | None = None) -> list[TrackedTicker]:
    # The latest staging_finnhub quote is the source of truth; the tickers snapshot
    # (a rounded copy refreshed by the sync) is only used when it is strictly newer
    # or there is no quote. Same-day ties go to the quote, so every page shows the
    # same price.
    sql = f"""
        SELECT
            t.symbol, {_DISPLAY_NAME} AS name, t.sector,
            CASE WHEN p."current" IS NOT NULL AND (t.price_as_of IS NULL OR p.as_of >= t.price_as_of)
                 THEN p."current" ELSE t.current_price END AS current_price,
            CASE WHEN p."current" IS NOT NULL AND (t.price_as_of IS NULL OR p.as_of >= t.price_as_of)
                 THEN p.percent_change ELSE t.change_percent END AS change_percent,
            GREATEST(p.as_of, t.price_as_of) AS price_as_of
        FROM tickers t
        LEFT JOIN ({_LATEST_PRICES}) p ON p.target_ticker = t.symbol
        {_COMPANY_NAMES_JOIN}
        {"WHERE t.symbol = %s" if symbol else ""}
        ORDER BY t.updated_at DESC
        LIMIT %s
    """
    rows = query_dict(sql, (symbol, limit) if symbol else (limit,))
    results = []
    for r in rows:
        row = dict(r)
        if row.get("price_as_of") is not None:
            row["price_as_of"] = row["price_as_of"].isoformat()
        results.append(TrackedTicker(**row))
    return results


_WORKSPACE_SELECT = """
    SELECT w.id, w.name, w.created_at, w.description, w.alert_on_filings,
           COALESCE(ARRAY_AGG(wt.ticker_symbol ORDER BY wt.ticker_symbol)
                    FILTER (WHERE wt.ticker_symbol IS NOT NULL), '{}') AS tickers,
           (SELECT COUNT(*) FROM alerts a
             WHERE a.user_id = w.user_id AND a.read IS NOT TRUE
               AND a.ticker IN (SELECT ticker_symbol FROM workspace_tickers WHERE workspace_id = w.id)) AS unread_alerts
    FROM workspaces w
    LEFT JOIN workspace_tickers wt ON wt.workspace_id = w.id
"""


def _workspace_row(r: dict) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=r["id"],
        name=r["name"],
        tickers=r["tickers"] or [],
        alerts=int(r.get("unread_alerts") or 0),
        created_at=r["created_at"].isoformat() if r["created_at"] else None,
        description=r.get("description"),
        alert_on_filings=bool(r.get("alert_on_filings")),
    )


def get_user_workspaces(user_id: int) -> list[WorkspaceResponse]:
    """The user's workspaces, newest first. Archived workspaces are hidden, not deleted."""
    rows = query_dict(
        _WORKSPACE_SELECT + """
        WHERE w.user_id = %s AND w.archived_at IS NULL
        GROUP BY w.id
        ORDER BY w.created_at DESC
        """,
        (user_id,),
    )
    return [_workspace_row(r) for r in rows]


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


def archive_workspace(user_id: int, workspace_id: int) -> None:
    """Hide a workspace from the user's list. The row and its tickers are kept."""
    from app.db import execute
    execute(
        "UPDATE workspaces SET archived_at = NOW() WHERE id = %s AND user_id = %s AND archived_at IS NULL",
        (workspace_id, user_id),
    )
    _sync_filing_alerts(user_id)


def update_workspace(user_id: int, workspace_id: int, name: str | None, description: str | None,
                     alert_on_filings: bool | None) -> None:
    from app.db import execute
    execute(
        """
        UPDATE workspaces
        SET name = COALESCE(%s, name),
            description = COALESCE(%s, description),
            alert_on_filings = COALESCE(%s, alert_on_filings)
        WHERE id = %s AND user_id = %s AND archived_at IS NULL
        """,
        (name, description, alert_on_filings, workspace_id, user_id),
    )
    if alert_on_filings is not None:
        _sync_filing_alerts(user_id)


def _sync_filing_alerts(user_id: int) -> None:
    """Keep "new SEC filing" subscriptions in line with workspaces that have alert_on_filings on.

    Every ticker in such a workspace gets an active filing subscription (created if
    missing). A filing subscription for a ticker no such workspace covers any more is
    paused, never deleted. Subscriptions the user manages on the Alerts page for
    tickers outside these workspaces are left alone.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH wanted AS (
                    SELECT DISTINCT wt.ticker_symbol AS ticker
                    FROM workspaces w JOIN workspace_tickers wt ON wt.workspace_id = w.id
                    WHERE w.user_id = %(u)s AND w.alert_on_filings AND w.archived_at IS NULL
                )
                INSERT INTO alert_subscriptions (user_id, ticker, alert_type, threshold, active)
                SELECT %(u)s, ticker, 'filing', NULL, TRUE FROM wanted
                ON CONFLICT (user_id, ticker, alert_type) DO UPDATE SET active = TRUE
                """,
                {"u": user_id},
            )
            cur.execute(
                """
                UPDATE alert_subscriptions s SET active = FALSE
                WHERE s.user_id = %(u)s AND s.alert_type = 'filing' AND s.active
                  AND s.ticker IN (SELECT wt.ticker_symbol FROM workspaces w
                                   JOIN workspace_tickers wt ON wt.workspace_id = w.id
                                   WHERE w.user_id = %(u)s)
                  AND s.ticker NOT IN (SELECT wt.ticker_symbol FROM workspaces w
                                       JOIN workspace_tickers wt ON wt.workspace_id = w.id
                                       WHERE w.user_id = %(u)s AND w.alert_on_filings AND w.archived_at IS NULL)
                """,
                {"u": user_id},
            )
        conn.commit()


def add_ticker_to_workspace(workspace_id: int, ticker_symbol: str, user_id: int | None = None) -> None:
    from app.db import execute
    sql = """
        INSERT INTO workspace_tickers (workspace_id, ticker_symbol)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """
    execute(sql, (workspace_id, ticker_symbol))
    if user_id is not None:
        _sync_filing_alerts(user_id)


def remove_ticker_from_workspace(workspace_id: int, ticker_symbol: str, user_id: int | None = None) -> None:
    from app.db import execute
    sql = """
        DELETE FROM workspace_tickers
        WHERE workspace_id = %s AND ticker_symbol = %s
    """
    execute(sql, (workspace_id, ticker_symbol))
    if user_id is not None:
        _sync_filing_alerts(user_id)


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
    sql = "SELECT 1 FROM workspaces WHERE id = %s AND user_id = %s AND archived_at IS NULL"
    rows = query_dict(sql, (workspace_id, user_id))
    return len(rows) > 0


def get_workspace_by_id(workspace_id: int, user_id: int) -> WorkspaceResponse | None:
    rows = query_dict(
        _WORKSPACE_SELECT + """
        WHERE w.id = %s AND w.user_id = %s AND w.archived_at IS NULL
        GROUP BY w.id
        """,
        (workspace_id, user_id),
    )
    return _workspace_row(rows[0]) if rows else None


def count_articles() -> tuple[int, int]:
    """Distinct news articles and distinct SEC filings, counted live at request time.

    News: staging_gnews (relational, loaded nightly). One article is stored once per
    ticker in its GNews batch, so it is counted by URL. The vectorized gnews/ files
    hold the same articles, so they are not added again.
    SEC filings: the union of the paused relational archive (staging_sec_archive) and
    the vectorized mirror (sec_vectorized_chunks), matched on the undashed accession
    number (the 4th path segment of SEC/{form}/{CIK}/{accession}/...), so a filing in
    both is counted once and new filings raise the count as they are vectorized.
    """
    # The archive has ~700 filings spread over ~750k element rows: walk its
    # accession index one distinct value at a time (a skip scan, ~25 ms) instead
    # of sorting every row (~550 ms).
    rows = query_dict(
        """
        WITH RECURSIVE archive AS (
            (SELECT accession_number AS acc FROM staging_sec_archive
             WHERE accession_number IS NOT NULL ORDER BY accession_number LIMIT 1)
            UNION ALL
            SELECT (SELECT accession_number FROM staging_sec_archive
                    WHERE accession_number > archive.acc ORDER BY accession_number LIMIT 1)
            FROM archive WHERE archive.acc IS NOT NULL
        )
        SELECT
            -- SELECT DISTINCT in a subquery lets Postgres walk the url index (~0.1 s on 400k rows);
            -- COUNT(DISTINCT url) sorts every row (~0.8 s)
            (SELECT COUNT(*) FROM (SELECT DISTINCT url FROM staging_gnews WHERE url IS NOT NULL AND url <> '') u) AS news,
            (SELECT COUNT(*) FROM (
                SELECT acc FROM archive WHERE acc IS NOT NULL
                UNION
                SELECT split_part(source_object, '/', 4) FROM sec_vectorized_chunks WHERE source_object LIKE 'SEC/%'
            ) filings) AS filings
        """
    )
    return int(rows[0]["news"]), int(rows[0]["filings"])


def get_user_alerts(user_id: int, limit: int = 10) -> list[AlertResponse]:
    sql = """
        SELECT id, ticker, type, message, read, severity, created_at, subscription_id
        FROM alerts
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    rows = query_dict(sql, (user_id, limit))
    return [_alert_row(r) for r in rows]


def _alert_row(r: dict) -> AlertResponse:
    return AlertResponse(
        id=r["id"],
        ticker=r["ticker"],
        type=r["type"],
        message=r["message"],
        read=r["read"],
        severity=r["severity"],
        time=r["created_at"].isoformat() if r["created_at"] else None,
        subscription_id=r.get("subscription_id"),
    )


def get_user_alert_summary(user_id: int) -> AlertSummary:
    """Unread count and the newest unread alert, for the bell, nav badge and pop-up."""
    count = query_dict("SELECT COUNT(*) AS n FROM alerts WHERE user_id = %s AND read IS NOT TRUE", (user_id,))
    newest = query_dict(
        """
        SELECT id, ticker, type, message, read, severity, created_at, subscription_id
        FROM alerts
        WHERE user_id = %s AND read IS NOT TRUE
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    return AlertSummary(unread_count=int(count[0]["n"]), newest_unread=_alert_row(newest[0]) if newest else None)


def mark_user_alerts_read(user_id: int, alert_ids: list[int] | None = None) -> int:
    """Mark the user's alerts read (all unread ones, or just alert_ids). Returns rows updated."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if alert_ids:
                cur.execute(
                    "UPDATE alerts SET read = TRUE WHERE user_id = %s AND read IS NOT TRUE AND id = ANY(%s)",
                    (user_id, alert_ids),
                )
            else:
                cur.execute("UPDATE alerts SET read = TRUE WHERE user_id = %s AND read IS NOT TRUE", (user_id,))
            updated = cur.rowcount
        conn.commit()
    return updated


# ─── Alert subscriptions ────────────────────────────────────────────────────
# Users subscribe to one thing per ticker (price above/below a threshold, new
# news, new SEC filing). Subscriptions are never deleted: turning one off sets
# active = FALSE. app/services/alert_evaluator.py checks them after each sync.

_SUBSCRIPTION_COLUMNS = """
    s.id, s.ticker, s.alert_type, s.threshold, s.active, s.created_at,
    st.last_observed_label, st.last_evaluated_at, st.last_alerted_at
"""


def _subscription_row(r: dict) -> "AlertSubscriptionResponse":
    from app.models import AlertSubscriptionResponse
    iso = lambda v: v.isoformat() if v is not None else None
    return AlertSubscriptionResponse(
        id=r["id"], ticker=r["ticker"], alert_type=r["alert_type"],
        threshold=float(r["threshold"]) if r["threshold"] is not None else None,
        active=r["active"], created_at=iso(r["created_at"]),
        last_observed_label=r.get("last_observed_label"),
        last_evaluated_at=iso(r.get("last_evaluated_at")), last_alerted_at=iso(r.get("last_alerted_at")),
    )


def get_user_subscriptions(user_id: int) -> list["AlertSubscriptionResponse"]:
    rows = query_dict(
        f"""
        SELECT {_SUBSCRIPTION_COLUMNS}
        FROM alert_subscriptions s
        LEFT JOIN alert_subscription_state st ON st.subscription_id = s.id
        WHERE s.user_id = %s
        ORDER BY s.ticker, s.alert_type
        """,
        (user_id,),
    )
    return [_subscription_row(r) for r in rows]


def get_user_subscription(user_id: int, subscription_id: int) -> "AlertSubscriptionResponse | None":
    rows = query_dict(
        f"""
        SELECT {_SUBSCRIPTION_COLUMNS}
        FROM alert_subscriptions s
        LEFT JOIN alert_subscription_state st ON st.subscription_id = s.id
        WHERE s.user_id = %s AND s.id = %s
        """,
        (user_id, subscription_id),
    )
    return _subscription_row(rows[0]) if rows else None


def ticker_exists(symbol: str) -> bool:
    return bool(query_dict("SELECT 1 FROM tickers WHERE symbol = %s", (symbol,)))


def create_user_subscription(user_id: int, ticker: str, alert_type: str, threshold: float | None) -> int | None:
    """Insert a subscription; returns its id, or None if the user already has this (ticker, type)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_subscriptions (user_id, ticker, alert_type, threshold, active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (user_id, ticker, alert_type) DO NOTHING
                RETURNING id
                """,
                (user_id, ticker, alert_type, threshold),
            )
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def update_user_subscription(user_id: int, subscription_id: int, active: bool | None, threshold: float | None) -> bool:
    """Toggle active and/or change threshold on the user's own subscription. False if not found."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alert_subscriptions
                SET active = COALESCE(%s, active),
                    threshold = COALESCE(%s, threshold)
                WHERE id = %s AND user_id = %s
                """,
                (active, threshold, subscription_id, user_id),
            )
            found = cur.rowcount == 1
        conn.commit()
    return found


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
