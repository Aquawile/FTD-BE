"""db_integration: this week's data path against a real Postgres shaped like staging.

Runs as ftd_app (the API's role), so missing grants fail here, not on staging.
Uses the seed rows from tests/schema/seed.sql.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
from datetime import date
from uuid import uuid4

import pytest

from app import crud
from app.db import get_connection, query_dict
from app.services import alert_evaluator

pytestmark = pytest.mark.db_integration

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_recent_relational", _ROOT / "scripts" / "sync_recent_relational.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Blob:
    def __init__(self, name: str, text: str):
        self.name, self._text = name, text

    def exists(self) -> bool:
        return True

    def download_as_text(self, encoding: str = "utf-8") -> str:
        return self._text


class _Bucket:
    """Stands in for raw-data-strg: prices/{date}/data.jsonl."""

    def __init__(self, files: dict[str, str]):
        self._blobs = {name: _Blob(name, text) for name, text in files.items()}

    def list_blobs(self, prefix: str):
        return [b for n, b in self._blobs.items() if n.startswith(prefix)]

    def blob(self, name: str) -> _Blob:
        return self._blobs[name]


def _quote(symbol: str, day: str, price: float) -> str:
    return json.dumps({"symbol": symbol, "timestamp": f"{day}T20:00:00Z", "current": price, "change": 1.0,
                       "percent_change": 0.4, "high": price + 2, "low": price - 2, "open": price - 1,
                       "previous_close": price - 1})


def _count(sql: str, params=()) -> int:
    return int(query_dict(sql, params)[0]["n"])


def _make_user() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (email, firebase_uid) VALUES (%s, %s) RETURNING id",
                        (f"db-test-{uuid4().hex[:8]}@example.com", f"uid-{uuid4().hex}"))
            user_id = cur.fetchone()[0]
        conn.commit()
    return user_id


class TestGrants:
    @pytest.mark.parametrize("table,privileges", [
        ("alert_subscriptions", ("SELECT", "INSERT", "UPDATE")),
        ("alert_subscription_state", ("SELECT", "INSERT", "UPDATE")),
        ("alerts", ("SELECT", "INSERT", "UPDATE")),
        ("staging_finnhub", ("SELECT", "INSERT")),
        ("staging_gnews", ("SELECT", "INSERT")),
        ("sec_vectorized_chunks", ("SELECT",)),
        ("tickers", ("SELECT", "UPDATE")),
        ("ticker_company_names", ("SELECT", "INSERT")),
        ("staging_sec_archive", ("SELECT",)),
    ])
    def test_app_role_can_use_table(self, table, privileges):
        for privilege in privileges:
            assert query_dict("SELECT has_table_privilege(current_user, %s, %s) AS ok", (table, privilege))[0]["ok"], \
                f"{privilege} on {table} not granted to the app role"


class TestPriceSyncInsertOnly:
    def test_second_run_inserts_nothing_and_nothing_is_removed(self):
        sync = _load_sync_module()
        bucket = _Bucket({
            "prices/2026-10-19/data.jsonl": "\n".join([_quote("AAPL", "2026-10-19", 350.0), _quote("NVDA", "2026-10-19", 220.0)]),
            "prices/2026-10-20/data.jsonl": "\n".join([_quote("AAPL", "2026-10-20", 351.0), _quote("NVDA", "2026-10-20", 221.0)]),
        })
        before = _count("SELECT COUNT(*) AS n FROM staging_finnhub")
        with get_connection() as conn:
            first = sync.sync_prices(conn, bucket, {"AAPL", "NVDA"}, {}, 3, False, since_override=date(2026, 10, 19))
            second = sync.sync_prices(conn, bucket, {"AAPL", "NVDA"}, {}, 3, False, since_override=date(2026, 10, 19))
        assert (first, second) == (4, 0)
        assert _count("SELECT COUNT(*) AS n FROM staging_finnhub") == before + 4

    def test_prices_endpoint_returns_one_row_per_day(self):
        rows = crud.get_ticker_prices("AAPL", date(2026, 10, 12), date(2026, 10, 31))
        days = [r.normalized_calendar_date for r in rows]
        assert days == sorted(set(days))


class TestTrackedTickers:
    def test_single_symbol_prefers_newer_quote_over_snapshot(self):
        [aapl] = crud.get_tracked_tickers(limit=1, symbol="AAPL")
        latest = query_dict("""SELECT "current" FROM staging_finnhub WHERE target_ticker = 'AAPL'
                               ORDER BY normalized_calendar_date DESC, ingest_date DESC LIMIT 1""")[0]["current"]
        assert aapl.current_price == float(latest)
        assert aapl.price_as_of > "2026-10-15T20:00:00"

    def test_full_list_includes_every_ticker(self):
        assert {t.symbol for t in crud.get_tracked_tickers()} >= {"AAPL", "NVDA", "MSFT"}


class TestAlertEvaluator:
    def test_fires_once_then_summary_and_mark_read(self):
        user_id = _make_user()
        sub_id = crud.create_user_subscription(user_id, "NVDA", "price_above", 100.0)
        assert sub_id is not None
        assert crud.create_user_subscription(user_id, "NVDA", "price_above", 100.0) is None  # duplicate

        first = [r for r in alert_evaluator.evaluate_subscriptions() if r["id"] == sub_id]
        second = [r for r in alert_evaluator.evaluate_subscriptions() if r["id"] == sub_id]
        assert first[0]["fired"] is True and second[0]["fired"] is False
        assert _count("SELECT COUNT(*) AS n FROM alerts WHERE subscription_id = %s", (sub_id,)) == 1

        summary = crud.get_user_alert_summary(user_id)
        assert summary.unread_count == 1 and summary.newest_unread.ticker == "NVDA"
        assert crud.get_user_subscription(user_id, sub_id).last_observed_label.startswith("$")

        assert crud.mark_user_alerts_read(user_id) == 1
        assert crud.get_user_alert_summary(user_id).unread_count == 0

    def test_paused_subscription_is_not_evaluated(self):
        user_id = _make_user()
        sub_id = crud.create_user_subscription(user_id, "MSFT", "news", None)
        crud.update_user_subscription(user_id, sub_id, False, None)
        assert all(r["id"] != sub_id for r in alert_evaluator.evaluate_subscriptions())

    def test_news_baseline_then_fires_on_new_article(self):
        user_id = _make_user()
        sub_id = crud.create_user_subscription(user_id, "AAPL", "news", None)
        [baseline] = [r for r in alert_evaluator.evaluate_subscriptions() if r["id"] == sub_id]
        assert baseline["fired"] is False
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO staging_gnews (target_ticker, element_type, content_body, normalized_calendar_date,
                                                          ingest_date, url)
                               VALUES ('AAPL', 'narrative', 'New AAPL article', '2026-10-20', now(), %s)""",
                            (f"https://example.com/{uuid4().hex}",))
            conn.commit()
        [after] = [r for r in alert_evaluator.evaluate_subscriptions() if r["id"] == sub_id]
        assert after["fired"] is True and "1 new news article for AAPL" in after["message"]


class TestArticleCount:
    def test_news_by_url_plus_sec_filings_across_archive_and_mirror(self):
        news, filings = crud.count_articles()
        assert news == _count("SELECT COUNT(DISTINCT url) AS n FROM staging_gnews")
        # Seed: 2 AAPL filings in the mirror; one also in the paused archive (undashed accession).
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO staging_sec_archive (target_ticker, accession_number, form_type, content_body)
                               VALUES ('AAPL', '000032019326000101', '10-K', 'archived element'),
                                      ('AAPL', '000032019326000101', '10-K', 'second element, same filing'),
                                      ('AAPL', '000032019324000999', '10-K', 'older filing only in the archive')""")
            conn.commit()
        assert crud.count_articles()[1] == filings + 1  # only the archive-only filing is new

    def test_new_article_raises_the_count(self):
        before = crud.count_articles()[0]
        with get_connection() as conn:
            with conn.cursor() as cur:
                url = f"https://example.com/{uuid4().hex}"
                cur.execute("""INSERT INTO staging_gnews (target_ticker, content_body, normalized_calendar_date, ingest_date, url)
                               VALUES ('AAPL', 'x', '2026-10-21', now(), %s), ('NVDA', 'x', '2026-10-21', now(), %s)""", (url, url))
            conn.commit()
        assert crud.count_articles()[0] == before + 1  # one article filed under two tickers counts once


class TestCompanyNames:
    def test_name_falls_back_to_company_name_and_is_searchable(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO tickers (symbol, name, sector) VALUES ('MMM', 'MMM', 'Industrials') ON CONFLICT DO NOTHING")
                cur.execute("INSERT INTO ticker_company_names (symbol, company_name, source) VALUES ('MMM', '3M', 'test') "
                            "ON CONFLICT DO NOTHING")
            conn.commit()
        [mmm] = crud.get_tracked_tickers(limit=1, symbol="MMM")
        assert mmm.name == "3M"
        assert [r.ticker for r in crud.search_tickers("3M")] == ["MMM"]
        assert query_dict("SELECT name FROM tickers WHERE symbol = 'MMM'")[0]["name"] == "MMM"  # source row untouched

    def test_curated_name_wins_over_company_name(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO ticker_company_names (symbol, company_name, source) VALUES ('AAPL', 'Apple', 'test') "
                            "ON CONFLICT DO NOTHING")
            conn.commit()
        [aapl] = crud.get_tracked_tickers(limit=1, symbol="AAPL")
        assert aapl.name == "Apple Inc."
        assert "AAPL" in [r.ticker for r in crud.search_tickers("apple")]

    def test_symbol_when_no_name_known(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO tickers (symbol, name) VALUES ('ZZZQ', 'ZZZQ') ON CONFLICT DO NOTHING")
            conn.commit()
        assert crud.get_tracked_tickers(limit=1, symbol="ZZZQ")[0].name == "ZZZQ"


class TestWorkspaceSettings:
    def _workspace(self, user_id, tickers):
        ws = crud.create_workspace(user_id, "Test WS", tickers)
        return ws.id

    def test_archive_hides_but_keeps_the_row(self):
        user_id = _make_user()
        ws_id = self._workspace(user_id, ["AAPL"])
        crud.archive_workspace(user_id, ws_id)
        assert ws_id not in [w.id for w in crud.get_user_workspaces(user_id)]
        assert _count("SELECT COUNT(*) AS n FROM workspaces WHERE id = %s AND archived_at IS NOT NULL", (ws_id,)) == 1
        assert _count("SELECT COUNT(*) AS n FROM workspace_tickers WHERE workspace_id = %s", (ws_id,)) == 1

    def test_rename_and_description_persist(self):
        user_id = _make_user()
        ws_id = self._workspace(user_id, [])
        crud.update_workspace(user_id, ws_id, "Renamed", "my notes", None)
        ws = crud.get_workspace_by_id(ws_id, user_id)
        assert (ws.name, ws.description) == ("Renamed", "my notes")

    def test_filing_alerts_follow_the_workspace_switch(self):
        user_id = _make_user()
        ws_id = self._workspace(user_id, ["AAPL", "NVDA"])
        active = lambda: {r["ticker"]: r["active"] for r in query_dict(
            "SELECT ticker, active FROM alert_subscriptions WHERE user_id = %s AND alert_type = 'filing'", (user_id,))}
        crud.update_workspace(user_id, ws_id, None, None, True)
        assert active() == {"AAPL": True, "NVDA": True}
        crud.add_ticker_to_workspace(ws_id, "MSFT", user_id=user_id)
        assert active()["MSFT"] is True
        crud.update_workspace(user_id, ws_id, None, None, False)
        assert set(active().values()) == {False}                        # paused, not deleted
        assert crud.get_workspace_by_id(ws_id, user_id).alert_on_filings is False

    def test_unread_alert_count_on_workspace(self):
        user_id = _make_user()
        ws_id = self._workspace(user_id, ["NVDA"])
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO alerts (user_id, ticker, type, message) VALUES (%s, 'NVDA', 'news', 'm'), (%s, 'AAPL', 'news', 'm')",
                            (user_id, user_id))
            conn.commit()
        assert crud.get_workspace_by_id(ws_id, user_id).alerts == 1
