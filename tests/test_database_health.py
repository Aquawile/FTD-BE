"""db_integration: the database integrity checks (scripts/check_database_health.py) against a real Postgres.

Two things are proven: a healthy database passes every check, and each kind of damage is actually caught
(the checks are not vacuous). All damage is made inside a transaction that is rolled back.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

from app.db import get_connection

pytestmark = pytest.mark.db_integration

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _health():
    spec = importlib.util.spec_from_file_location("check_database_health", _ROOT / "scripts" / "check_database_health.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _failed(conn) -> set[str]:
    return {c.name for c in _health().run_checks(conn) if not c.ok}


def _scrub_other_tests_leftovers(cur) -> None:
    # Other db tests leave rows behind (for example news under a made-up ticker). Remove them inside this transaction only.
    cur.execute("DELETE FROM staging_gnews WHERE target_ticker NOT IN (SELECT symbol FROM tickers)")
    cur.execute("DELETE FROM staging_finnhub WHERE target_ticker NOT IN (SELECT symbol FROM tickers)")
    cur.execute("""DELETE FROM staging_finnhub a USING staging_finnhub b
                   WHERE a.ctid > b.ctid AND a.target_ticker = b.target_ticker AND a.normalized_calendar_date::date = b.normalized_calendar_date::date""")


@pytest.fixture
def conn():
    with get_connection() as c:
        c.rollback()
        c.autocommit = False
        with c.cursor() as cur:
            _scrub_other_tests_leftovers(cur)
        yield c
        c.rollback()


def test_a_healthy_database_passes_every_check(conn):
    assert _failed(conn) == set()


def test_each_kind_of_damage_is_caught(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT target_ticker, target_cik, normalized_calendar_date FROM staging_finnhub ORDER BY normalized_calendar_date DESC LIMIT 1")
        sym, cik, day = cur.fetchone()
        cols = '(target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, symbol, "timestamp", "current", change, percent_change)'
        # a second row for the same ticker and day
        cur.execute(f"INSERT INTO staging_finnhub {cols} VALUES (%s, %s, 'quantitative', '', %s, now(), %s, now(), 10, 0, 0)", (sym, cik, day, sym))
        # a zero price on another day, and an absurd move
        cur.execute(f"INSERT INTO staging_finnhub {cols} VALUES (%s, %s, 'quantitative', '', '2020-01-02', now(), %s, now(), 0, 0, 95)", (sym, cik, sym))
        # news for a ticker nobody tracks, and a news row with no text
        cur.execute("INSERT INTO staging_gnews (target_ticker, element_type, content_body, normalized_calendar_date, ingest_date, url) VALUES ('ZZUNTRACKED', 'narrative', '', '2026-01-01', '2026-01-02', 'https://example.com/x')")
        # a tracked ticker with no price
        cur.execute("INSERT INTO tickers (symbol, name, sector) VALUES ('ZZNOPRICE', 'No Price Inc', 'Test')")
        # a permission granted without updating the index the API reads
        cur.execute("""INSERT INTO users (email, firebase_uid) VALUES ('health.check@example.test', 'health-check-uid') RETURNING id""")
        uid = cur.fetchone()[0]
        cur.execute("INSERT INTO user_permissions (user_id, permission_id) SELECT %s, id FROM permissions LIMIT 1", (uid,))
        # two users with the same email in different case, and an empty Firebase uid
        cur.execute("INSERT INTO users (email, firebase_uid) VALUES ('HEALTH.CHECK@example.test', '')")
    failed = _failed(conn)
    assert {
        "no duplicate price rows (ticker + quote day)",
        "no zero or negative prices",
        "no absurd daily moves (over 80%)",
        "every ticker with prices or news is tracked",
        "news rows carry text and a date",
        "every tracked ticker has a price",
        "every tracked ticker has a quote row",
        "every user permission is in the index the API reads",
        "no empty Firebase uids",
        "one application user per email (case-insensitive)",
    } <= failed
