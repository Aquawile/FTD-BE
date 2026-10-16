"""Unit tests for the pandas-built 365-day price timeline."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.services.price_timeline import build_price_timeline

pytestmark = pytest.mark.unit


def _row(day: date, close: float):
    return {"day": day, "close": close, "open": close - 1, "high": close + 1, "low": close - 2, "percent_change": 0.5}


def _build(rows, **kwargs):
    with patch("app.services.price_timeline.query_dict", return_value=rows):
        return build_price_timeline("nvda", **kwargs)


def test_partial_history_anchors_window_at_first_quote_and_leaves_rest_empty():
    first = date(2026, 7, 2)  # Thursday
    rows = [_row(first, 100.0), _row(first + timedelta(days=1), 101.0), _row(first + timedelta(days=4), 102.0)]
    tl = _build(rows)

    assert tl.ticker == "NVDA"
    assert tl.window_start == first
    assert tl.window_end == first + timedelta(days=364)
    assert len(tl.points) == 365
    assert tl.trading_days == 3
    assert tl.days_covered == 5
    assert tl.fill_ratio == round(5 / 365, 4)
    # weekend between quotes and every future day stay empty, nothing interpolated
    assert tl.points[2].has_data is False and tl.points[2].close is None
    assert tl.points[4].close == 102.0
    assert all(p.close is None for p in tl.points[5:])


def test_full_history_becomes_rolling_window_ending_on_latest_quote():
    start = date(2025, 1, 1)
    rows = [_row(start + timedelta(days=i), 50.0 + i) for i in range(400)]
    tl = _build(rows)

    last = start + timedelta(days=399)
    assert tl.window_end == last
    assert tl.window_start == last - timedelta(days=364)
    assert len(tl.points) == 365
    assert tl.trading_days == 365
    assert tl.fill_ratio == 1.0
    assert tl.points[-1].close == 50.0 + 399


def test_no_quotes_returns_empty_timeline():
    tl = _build([])
    assert tl.points == []
    assert tl.window_start is None
    assert tl.trading_days == 0


def test_duplicate_day_keeps_latest_ingested_quote():
    d = date(2026, 7, 2)
    tl = _build([_row(d, 100.0), _row(d, 105.0)])
    assert tl.trading_days == 1
    assert tl.points[0].close == 105.0


def test_custom_window_length():
    d = date(2026, 7, 2)
    tl = _build([_row(d, 100.0)], window_days=30)
    assert len(tl.points) == 30
    assert tl.window_end == d + timedelta(days=29)
