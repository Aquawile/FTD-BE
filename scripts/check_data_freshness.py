#!/usr/bin/env python3
"""Read-only check that the data the app serves is current.

Run daily by .github/workflows/data-freshness.yml (01:00 UTC, after the 00:20
sync) on ftd-staging-api with the ftd-api service's PG* env. Prints a Markdown
report and exits 1 if anything is behind:

  prices      newest staging_finnhub quote vs the last US trading day whose
              prices should be loaded (close 20:00 UTC, fetch 22:09, sync 22:20).
              One business day of slack covers market holidays; weekends never count.
  news        newest staging_gnews ingest within NEWS_MAX_AGE_HOURS
  vectorized  newest sec_vectorized_chunks.vectorized_at within VECTOR_MAX_AGE_HOURS
              (prices are vectorized daily, so this moves every day)
  sync        the last sync_all_recent.sh run finished with status=0 within SYNC_MAX_AGE_HOURS

Usage: python3 scripts/check_data_freshness.py [--log PATH] [--skip-sync-log]
  --skip-sync-log  used when run as the last step *inside* the sync, whose own
                   "finished" line isn't written yet
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

PRICE_SLACK_BUSINESS_DAYS = 1
NEWS_MAX_AGE_HOURS = 30
VECTOR_MAX_AGE_HOURS = 30
SYNC_MAX_AGE_HOURS = 26
PRICES_LOADED_BY = time(22, 30)   # UTC: after the 22:20 sync
DEFAULT_LOG = "/home/isabellabutera/prices/sync_all_recent.log"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def expected_trading_day(now: datetime) -> date:
    """Most recent weekday whose closing prices should already be in Postgres."""
    day = now.date() if now.time() >= PRICES_LOADED_BY else now.date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def business_days_behind(newest: date, expected: date) -> int:
    """Weekdays after `newest` up to and including `expected`."""
    behind, day = 0, newest
    while day < expected:
        day += timedelta(days=1)
        if day.weekday() < 5:
            behind += 1
    return behind


def check_prices(newest: date | None, now: datetime) -> Check:
    expected = expected_trading_day(now)
    if newest is None:
        return Check("prices", False, "no quotes in staging_finnhub")
    behind = business_days_behind(newest, expected)
    ok = behind <= PRICE_SLACK_BUSINESS_DAYS
    return Check("prices", ok, f"newest quote {newest}, expected {expected} ({behind} trading day(s) behind)")


def check_age(name: str, newest: datetime | None, now: datetime, max_hours: int) -> Check:
    if newest is None:
        return Check(name, False, "no rows")
    if newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    age = (now - newest).total_seconds() / 3600
    return Check(name, age <= max_hours, f"newest {newest:%Y-%m-%d %H:%M} UTC ({age:.1f} h old, limit {max_hours} h)")


_FINISHED = re.compile(r"=== finished at (.+?) \(status=(\d+)\) ===")


def check_sync_log(text: str, now: datetime) -> Check:
    runs = _FINISHED.findall(text)
    if not runs:
        return Check("sync", False, "no finished run in the sync log")
    when_raw, status = runs[-1]
    when = datetime.strptime(when_raw.replace(" UTC", ""), "%a %b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
    age = (now - when).total_seconds() / 3600
    ok = status == "0" and age <= SYNC_MAX_AGE_HOURS
    return Check("sync", ok, f"last run finished {when:%Y-%m-%d %H:%M} UTC with status={status} ({age:.1f} h ago)")


def report(checks: list[Check], now: datetime) -> str:
    lines = [f"## Data freshness — {now:%Y-%m-%d %H:%M} UTC", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines += [f"| {c.name} | {'✅ current' if c.ok else '❌ behind'} | {c.detail} |" for c in checks]
    return "\n".join(lines)


def main() -> int:
    import psycopg2

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--skip-sync-log", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)

    with psycopg2.connect("") as conn, conn.cursor() as cur:
        cur.execute("SELECT MAX(normalized_calendar_date)::date FROM staging_finnhub")
        newest_quote = cur.fetchone()[0]
        cur.execute("SELECT MAX(ingest_date) FROM staging_gnews")
        newest_news = cur.fetchone()[0]
        cur.execute("SELECT MAX(vectorized_at) FROM sec_vectorized_chunks")
        newest_vector = cur.fetchone()[0]
    checks = [
        check_prices(newest_quote, now),
        check_age("news", newest_news, now, NEWS_MAX_AGE_HOURS),
        check_age("vectorized", newest_vector, now, VECTOR_MAX_AGE_HOURS),
    ]
    if not args.skip_sync_log:
        try:
            with open(args.log, encoding="utf-8", errors="replace") as fh:
                log_text = fh.read()[-200_000:]
        except OSError as exc:
            log_text = ""
            print(f"(could not read {args.log}: {exc})", file=sys.stderr)
        checks.append(check_sync_log(log_text, now))
    print(report(checks, now))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
