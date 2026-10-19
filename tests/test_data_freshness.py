"""Decision logic of scripts/check_data_freshness.py (no database)."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from datetime import date, datetime, timezone

import pytest

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "check_data_freshness", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "check_data_freshness.py")
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m  # @dataclass looks its module up here
_spec.loader.exec_module(m)

UTC = timezone.utc


@pytest.mark.parametrize("now,expected", [
    (datetime(2026, 10, 20, 1, 0, tzinfo=UTC), date(2026, 10, 19)),   # Tue 01:00 -> Mon
    (datetime(2026, 10, 19, 1, 0, tzinfo=UTC), date(2026, 10, 16)),   # Mon 01:00 -> Fri
    (datetime(2026, 10, 18, 12, 0, tzinfo=UTC), date(2026, 10, 16)),  # Sun -> Fri
    (datetime(2026, 10, 19, 23, 0, tzinfo=UTC), date(2026, 10, 19)),  # Mon after the 22:20 sync -> Mon
])
def test_expected_trading_day(now, expected):
    assert m.expected_trading_day(now) == expected


def test_weekend_is_never_stale():
    assert m.check_prices(date(2026, 10, 16), datetime(2026, 10, 18, 12, tzinfo=UTC)).ok   # Fri quote on Sunday


def test_one_holiday_is_tolerated_two_days_are_not():
    tue = datetime(2026, 10, 21, 1, 0, tzinfo=UTC)                                          # expects Tue 20
    assert m.check_prices(date(2026, 10, 19), tue).ok                                       # 1 day behind
    assert not m.check_prices(date(2026, 10, 16), tue).ok                                   # 2 days behind


def test_age_checks():
    now = datetime(2026, 10, 20, 1, 0, tzinfo=UTC)
    assert m.check_age("news", datetime(2026, 10, 19, 0, 20), now, 30).ok
    assert not m.check_age("news", datetime(2026, 10, 17, 0, 20), now, 30).ok
    assert not m.check_age("news", None, now, 30).ok


def test_sync_log():
    now = datetime(2026, 10, 19, 1, 0, tzinfo=UTC)
    good = "=== finished at Mon Oct 19 00:20:28 UTC 2026 (status=0) ==="
    assert m.check_sync_log("noise\n" + good, now).ok
    assert not m.check_sync_log(good.replace("status=0", "status=1"), now).ok
    assert not m.check_sync_log("=== finished at Fri Oct 16 00:20:28 UTC 2026 (status=0) ===", now).ok
    assert not m.check_sync_log("", now).ok
