#!/usr/bin/env python3
"""Read-only integrity checks for the application database (PG* environment).

What it proves, in plain terms: the tables the app reads exist, every migration applied, no index is
invalid, no price row is duplicated or nonsensical, nothing points at a record that is gone, every
tracked ticker has a price, and each user's permission index matches their grants.

Data freshness (is yesterday's data in?) is a separate nightly check: scripts/check_data_freshness.py.

    python3 scripts/check_database_health.py          # prints a table, exit 1 if anything fails
    python3 scripts/check_database_health.py --json

run_checks(conn) is also what tests/test_database_health.py runs against the CI database,
including deliberately broken data, to show each check can fail.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import NamedTuple

REQUIRED_TABLES = [
    "tickers", "staging_finnhub", "staging_gnews", "sec_vectorized_chunks", "fiscal_parameters", "ticker_company_names",
    "users", "permissions", "user_permissions", "user_permissions_index",
    "workspaces", "workspace_tickers", "alerts", "alert_subscriptions", "alert_subscription_state",
    "api_usage_log", "schema_migrations",
]


class Check(NamedTuple):
    name: str
    ok: bool
    detail: str


def _scalar(cur, sql, args=None):
    cur.execute(sql, args)
    return cur.fetchone()[0]


def run_checks(conn) -> list[Check]:
    out: list[Check] = []
    cur = conn.cursor()

    def check(name: str, bad_count_sql: str, what: str, args=None):
        n = _scalar(cur, bad_count_sql, args)
        out.append(Check(name, n == 0, f"{n} {what}" if n else "none"))

    missing = [t for t in REQUIRED_TABLES if _scalar(cur, "SELECT to_regclass(%s) IS NULL", (f"public.{t}",))]
    out.append(Check("required tables exist", not missing, f"missing: {missing}" if missing else f"all {len(REQUIRED_TABLES)} present"))

    check("every migration applied", "SELECT count(*) FROM schema_migrations WHERE NOT success", "failed migration rows")
    check("no invalid indexes", "SELECT count(*) FROM pg_index WHERE NOT indisvalid", "invalid indexes")

    check("no duplicate price rows (ticker + quote day)",
          "SELECT count(*) FROM (SELECT 1 FROM staging_finnhub GROUP BY target_ticker, normalized_calendar_date::date HAVING count(*) > 1) x",
          "ticker/day pairs with more than one row")
    check("no zero or negative prices",
          'SELECT count(*) FROM staging_finnhub WHERE "current" IS NOT NULL AND "current" <= 0', "rows")
    check("no absurd daily moves (over 80%)",
          "SELECT count(*) FROM staging_finnhub WHERE abs(percent_change) > 80", "rows")

    check("every ticker with prices or news is tracked",
          """SELECT count(*) FROM (
               SELECT target_ticker FROM staging_finnhub UNION SELECT target_ticker FROM staging_gnews) s
             WHERE NOT EXISTS (SELECT 1 FROM tickers t WHERE t.symbol = s.target_ticker)""",
          "symbols in prices/news that are not in tickers")
    check("every tracked ticker has a price",
          "SELECT count(*) FROM tickers WHERE current_price IS NULL", "tickers without a price")
    check("every tracked ticker has a quote row",
          "SELECT count(*) FROM tickers t WHERE NOT EXISTS (SELECT 1 FROM staging_finnhub f WHERE f.target_ticker = t.symbol)",
          "tickers with no quote row")

    check("no workspace tickers without their workspace",
          "SELECT count(*) FROM workspace_tickers w WHERE NOT EXISTS (SELECT 1 FROM workspaces x WHERE x.id = w.workspace_id)", "orphans")
    check("no alerts without their user",
          "SELECT count(*) FROM alerts a WHERE a.user_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.user_id)", "orphans")
    check("no subscriptions without their user",
          "SELECT count(*) FROM alert_subscriptions s WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = s.user_id)", "orphans")

    check("every user permission is in the index the API reads",
          """SELECT count(*) FROM user_permissions up JOIN permissions p ON p.id = up.permission_id
             WHERE NOT EXISTS (SELECT 1 FROM user_permissions_index i WHERE i.user_id = up.user_id AND i.permission_name = p.name)""",
          "grants missing from user_permissions_index")
    check("no empty Firebase uids",
          "SELECT count(*) FROM users WHERE firebase_uid IS NOT NULL AND firebase_uid = ''", "users with an empty Firebase uid")
    check("one application user per Firebase uid",
          "SELECT count(*) FROM (SELECT 1 FROM users WHERE firebase_uid IS NOT NULL GROUP BY firebase_uid HAVING count(*) > 1) x", "duplicated uids")
    check("one application user per email (case-insensitive)",
          "SELECT count(*) FROM (SELECT 1 FROM users GROUP BY lower(email) HAVING count(*) > 1) x", "duplicated emails")

    check("news rows carry text and a date",
          "SELECT count(*) FROM staging_gnews WHERE content_body IS NULL OR content_body = '' OR normalized_calendar_date IS NULL", "rows")
    return out


def main() -> int:
    import psycopg2

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    conn = psycopg2.connect(host=os.environ["PGHOST"], port=os.environ.get("PGPORT", "5432"), dbname=os.environ["PGDATABASE"],
                            user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"])
    conn.set_session(readonly=True, autocommit=True)
    checks = run_checks(conn)
    if args.json:
        print(json.dumps([c._asdict() for c in checks], indent=1))
    else:
        for c in checks:
            print(f"{'PASS' if c.ok else 'FAIL'}  {c.name:<58} {c.detail}")
        print(f"\n{sum(c.ok for c in checks)} of {len(checks)} checks passed")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
