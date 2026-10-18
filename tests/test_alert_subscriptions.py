"""Alert subscriptions: routes (only the user's real subscriptions) and the
end-of-sync evaluator (alerts only when a watched value changes)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_application_user
from app.auth.models import User
from app.main import app
from app.models import AlertSubscriptionResponse
from app.services import alert_evaluator as ev

pytestmark = pytest.mark.unit

client = TestClient(app)
_USER = User(id=4, firebase_uid="uid", email="test@example.com", is_active=True,
             created_at="2026-01-01T00:00:00", updated_at="2026-01-01T00:00:00")
_H = {"Authorization": "Bearer fake-valid-token"}


@pytest.fixture(autouse=True)
def _auth():
    async def _fake_user(request=None) -> User:
        return _USER
    app.dependency_overrides[get_current_application_user] = _fake_user
    with patch("app.auth.middleware.validate_firebase_token_with_reason",
               return_value=({"firebase_uid": "uid", "email": "test@example.com"}, None)), patch("app.db.execute"):
        yield
    app.dependency_overrides.pop(get_current_application_user, None)


def _sub(**kw) -> AlertSubscriptionResponse:
    base = dict(id=8, ticker="AAPL", alert_type="price_above", threshold=200.0, active=True)
    return AlertSubscriptionResponse(**{**base, **kw})


# ─── Routes ──────────────────────────────────────────────────────────────────

class TestSubscriptionRoutes:
    def test_no_subscriptions_means_empty_list(self):
        with patch("app.routes.alerts.get_user_subscriptions", return_value=[]) as m:
            r = client.get("/alerts/subscriptions", headers=_H)
        assert r.status_code == 200 and r.json() == []
        m.assert_called_once_with(4)

    def test_lists_only_the_users_subscriptions(self):
        with patch("app.routes.alerts.get_user_subscriptions", return_value=[_sub()]):
            r = client.get("/alerts/subscriptions", headers=_H)
        assert [s["ticker"] for s in r.json()] == ["AAPL"]

    def test_create_price_subscription(self):
        with patch("app.routes.alerts.ticker_exists", return_value=True), \
             patch("app.routes.alerts.create_user_subscription", return_value=8) as create, \
             patch("app.routes.alerts.get_user_subscription", return_value=_sub()):
            r = client.post("/alerts/subscriptions", headers=_H,
                            json={"ticker": " aapl ", "alert_type": "price_above", "threshold": 200})
        assert r.status_code == 201
        create.assert_called_once_with(4, "AAPL", "price_above", 200.0)

    def test_price_subscription_needs_threshold(self):
        r = client.post("/alerts/subscriptions", headers=_H, json={"ticker": "AAPL", "alert_type": "price_below"})
        assert r.status_code == 422

    def test_news_subscription_rejects_threshold(self):
        r = client.post("/alerts/subscriptions", headers=_H,
                        json={"ticker": "AAPL", "alert_type": "news", "threshold": 5})
        assert r.status_code == 422

    def test_unknown_alert_type_rejected(self):
        r = client.post("/alerts/subscriptions", headers=_H, json={"ticker": "AAPL", "alert_type": "hype"})
        assert r.status_code == 422

    def test_unknown_ticker_404(self):
        with patch("app.routes.alerts.ticker_exists", return_value=False):
            r = client.post("/alerts/subscriptions", headers=_H, json={"ticker": "ZZZZ", "alert_type": "news"})
        assert r.status_code == 404

    def test_duplicate_409(self):
        with patch("app.routes.alerts.ticker_exists", return_value=True), \
             patch("app.routes.alerts.create_user_subscription", return_value=None):
            r = client.post("/alerts/subscriptions", headers=_H, json={"ticker": "AAPL", "alert_type": "news"})
        assert r.status_code == 409

    def test_toggle_own_subscription(self):
        with patch("app.routes.alerts.get_user_subscription", side_effect=[_sub(), _sub(active=False)]), \
             patch("app.routes.alerts.update_user_subscription") as upd:
            r = client.patch("/alerts/subscriptions/8", headers=_H, json={"active": False})
        assert r.status_code == 200 and r.json()["active"] is False
        upd.assert_called_once_with(4, 8, False, None)

    def test_cannot_toggle_someone_elses_subscription(self):
        with patch("app.routes.alerts.get_user_subscription", return_value=None), \
             patch("app.routes.alerts.update_user_subscription") as upd:
            r = client.patch("/alerts/subscriptions/9", headers=_H, json={"active": False})
        assert r.status_code == 404
        upd.assert_not_called()

    def test_threshold_change_on_news_rejected(self):
        with patch("app.routes.alerts.get_user_subscription", return_value=_sub(alert_type="news", threshold=None)):
            r = client.patch("/alerts/subscriptions/8", headers=_H, json={"threshold": 10})
        assert r.status_code == 422

    def test_no_delete_route(self):
        assert client.delete("/alerts/subscriptions/8", headers=_H).status_code == 405

    def test_summary_with_unread(self):
        from app.models import AlertResponse, AlertSummary
        newest = AlertResponse(id=5, ticker="NVDA", type="price_above", message="NVDA closed above $150.00", read=False)
        with patch("app.routes.alerts.get_user_alert_summary",
                   return_value=AlertSummary(unread_count=2, newest_unread=newest)) as m:
            r = client.get("/alerts/summary", headers=_H)
        assert r.status_code == 200
        assert r.json()["unread_count"] == 2 and r.json()["newest_unread"]["id"] == 5
        m.assert_called_once_with(4)

    def test_summary_when_nothing_unread(self):
        from app.models import AlertSummary
        with patch("app.routes.alerts.get_user_alert_summary", return_value=AlertSummary()):
            r = client.get("/alerts/summary", headers=_H)
        assert r.json() == {"unread_count": 0, "newest_unread": None}

    def test_summary_requires_auth(self):
        app.dependency_overrides.pop(get_current_application_user, None)
        with patch("app.auth.middleware.validate_firebase_token_with_reason", return_value=(None, "missing")):
            assert client.get("/alerts/summary").status_code == 401

    def test_mark_all_read(self):
        with patch("app.routes.alerts.mark_user_alerts_read", return_value=3) as m:
            r = client.post("/alerts/read", headers=_H, json={})
        assert r.json() == {"updated": 3}
        m.assert_called_once_with(4, None)

    def test_mark_some_read(self):
        with patch("app.routes.alerts.mark_user_alerts_read", return_value=1) as m:
            client.post("/alerts/read", headers=_H, json={"alert_ids": [5]})
        m.assert_called_once_with(4, [5])


# ─── Evaluator decisions ─────────────────────────────────────────────────────

class TestPriceDecisions:
    def obs(self, close, kind="price_above", threshold=200.0):
        return ev.observe_price(kind, threshold, close, date(2026, 10, 15))

    def test_first_check_fires_when_already_above(self):
        d = ev.decide("price_above", "AAPL", 200.0, None, self.obs(342.0))
        assert d.fire and "AAPL closed above $200.00" in d.message

    def test_first_check_silent_when_not_met(self):
        assert not ev.decide("price_above", "AAPL", 200.0, None, self.obs(150.0)).fire

    def test_stays_above_does_not_refire(self):
        assert not ev.decide("price_above", "AAPL", 200.0, "met", self.obs(350.0)).fire

    def test_crossing_back_and_up_again_fires(self):
        assert not ev.decide("price_above", "AAPL", 200.0, "met", self.obs(190.0)).fire
        assert ev.decide("price_above", "AAPL", 200.0, "not_met", self.obs(210.0)).fire

    def test_price_below(self):
        o = self.obs(140.0, "price_below", 150.0)
        assert o.value == "met"
        assert ev.decide("price_below", "NVDA", 150.0, "not_met", o).fire

    def test_equal_to_threshold_is_not_a_cross(self):
        assert self.obs(200.0).value == "not_met"

    def test_no_price_data_means_no_observation(self):
        assert ev.observe_price("price_above", 200.0, None, None) is None


class TestCountDecisions:
    def test_first_check_is_baseline_only(self):
        assert not ev.decide("news", "NVDA", None, None, ev.observe_count("news", 188, date(2026, 10, 14))).fire

    def test_new_articles_fire(self):
        d = ev.decide("news", "NVDA", None, "188", ev.observe_count("news", 191, date(2026, 10, 15)))
        assert d.fire and d.message.startswith("3 new news articles for NVDA")

    def test_new_filing_fires_singular(self):
        d = ev.decide("filing", "NVDA", None, "4", ev.observe_count("filing", 5, date(2026, 10, 15)))
        assert d.fire and d.message.startswith("1 new SEC filing for NVDA")

    def test_unchanged_count_silent(self):
        assert not ev.decide("filing", "NVDA", None, "4", ev.observe_count("filing", 4, None)).fire


# ─── Runner ──────────────────────────────────────────────────────────────────

def _fake_conn():
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cm = MagicMock()
    cm.__enter__.return_value = conn
    return cm, conn, cur


class TestRunner:
    SUBS = [
        {"id": 8, "user_id": 81, "ticker": "AAPL", "alert_type": "price_above", "threshold": 200, "last_observed_value": None},
        {"id": 10, "user_id": 81, "ticker": "NVDA", "alert_type": "news", "threshold": None, "last_observed_value": "188"},
    ]

    def _run(self, dry_run):
        cm, conn, cur = _fake_conn()
        with patch.object(ev, "query_dict", return_value=self.SUBS), \
             patch.object(ev, "_latest_close", return_value=(342.0, date(2026, 10, 15))), \
             patch.object(ev, "_news_count", return_value=(188, date(2026, 10, 14))), \
             patch.object(ev, "get_connection", return_value=cm) as gc:
            results = ev.evaluate_subscriptions(dry_run=dry_run)
        return results, gc, conn, cur

    def test_inserts_alert_only_for_changed_and_records_state_for_all(self):
        results, _, conn, cur = self._run(dry_run=False)
        assert [r["fired"] for r in results] == [True, False]
        sql = [c.args[0] for c in cur.execute.call_args_list]
        assert sum("INSERT INTO alerts" in s for s in sql) == 1
        assert sum("alert_subscription_state" in s for s in sql) == 2
        assert not any("DELETE" in s.upper() or "TRUNCATE" in s.upper() for s in sql)
        insert = next(c for c in cur.execute.call_args_list if "INSERT INTO alerts" in c.args[0])
        assert insert.args[1][:3] == (81, "AAPL", "price_above") and insert.args[1][-1] == 8
        assert conn.commit.call_count == 2

    def test_dry_run_writes_nothing(self):
        results, gc, _, _ = self._run(dry_run=True)
        assert results[0]["fired"] is True
        gc.assert_not_called()
