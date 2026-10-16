"""Build a fixed-length daily price timeline for a ticker from staging_finnhub.

The window is ``window_days`` calendar days long (default 365):

* While a ticker has less than a full window of history, the window starts at its
  first finnhub quote and extends forward, so the chart fills in day by day as
  the nightly sync (scripts/sync_all_recent.sh) adds new quotes.
* Once history exceeds the window, it becomes a rolling window ending on the
  latest quote.

Only quotes we actually have are filled in. Weekends, holidays and future days
stay empty (``has_data = False``, prices ``None``); nothing is interpolated.
"""
from __future__ import annotations

import math

import pandas as pd

from app.db import query_dict
from app.models import PriceTimeline, PriceTimelinePoint

DEFAULT_WINDOW_DAYS = 365
_PRICE_COLUMNS = ["close", "open", "high", "low", "percent_change"]


def _load_quotes(ticker: str) -> pd.DataFrame:
    rows = query_dict(
        """
        SELECT normalized_calendar_date::date AS day,
               "current" AS close, open, high, low, percent_change
        FROM staging_finnhub
        WHERE target_ticker = %s AND "current" IS NOT NULL
        ORDER BY normalized_calendar_date, ingest_date NULLS FIRST
        """,
        (ticker,),
    )
    if not rows:
        return pd.DataFrame(columns=["day", *_PRICE_COLUMNS])
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    df[_PRICE_COLUMNS] = df[_PRICE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    # One quote per calendar day; the most recently ingested wins.
    return df.drop_duplicates(subset="day", keep="last")


def _clean(value) -> float | None:
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) else round(value, 4)


def build_price_timeline(ticker: str, window_days: int = DEFAULT_WINDOW_DAYS) -> PriceTimeline:
    ticker = ticker.upper()
    quotes = _load_quotes(ticker)
    if quotes.empty:
        return PriceTimeline(ticker=ticker, window_days=window_days)

    first, last = quotes["day"].min(), quotes["day"].max()
    span = pd.Timedelta(days=window_days - 1)
    if last - first < span:
        start, end = first, first + span          # filling up toward a full window
    else:
        start, end = last - span, last            # full: rolling window

    calendar = pd.date_range(start, end, freq="D", name="day")
    frame = quotes.set_index("day").reindex(calendar)
    frame["has_data"] = frame["close"].notna()

    points = [
        PriceTimelinePoint(
            date=day.date(),
            has_data=bool(row.has_data),
            **{col: _clean(getattr(row, col)) for col in _PRICE_COLUMNS},
        )
        for day, row in zip(frame.index, frame.itertuples(index=False))
    ]
    days_covered = int((min(last, end) - start).days) + 1
    return PriceTimeline(
        ticker=ticker,
        window_days=window_days,
        window_start=start.date(),
        window_end=end.date(),
        first_data_date=first.date(),
        last_data_date=last.date(),
        trading_days=int(frame["has_data"].sum()),
        days_covered=days_covered,
        fill_ratio=round(days_covered / window_days, 4),
        points=points,
    )
