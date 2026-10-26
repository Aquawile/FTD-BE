"""Evaluate alert subscriptions after each data sync.

A ticker's data only changes when the sync loads new prices, news or SEC
filings, so this runs once at the end of each sync (scripts/sync_all_recent.sh
-> scripts/evaluate_alert_subscriptions.py), never per request.

For every active subscription it observes the current value of what the user
watches, compares it with the last value recorded in alert_subscription_state,
and inserts an alert only when it changed:

  price_above / price_below  latest close crosses the threshold (fires once per
                             crossing; again only after it crosses back)
  news                       new articles stored for the ticker
  filing                     new SEC filing in the vectorized mirror

The first evaluation of a news/filing subscription only records a baseline (no
alert for history). A price subscription fires on its first evaluation if the
condition already holds. Nothing is ever deleted: alerts are inserted and the
state row is updated in place.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.db import get_connection, query_dict

logger = logging.getLogger(__name__)

SEVERITY = {"price_above": "high", "price_below": "high", "filing": "medium", "news": "low"}


@dataclass(frozen=True)
class Observation:
    value: str          # compared with the previous run's value
    label: str          # human-readable current state, shown in the UI
    detail: str = ""    # extra context for the alert message


@dataclass(frozen=True)
class Decision:
    fire: bool
    message: str | None = None


# ─── Pure decisions (no I/O) ─────────────────────────────────────────────────

def observe_price(alert_type: str, threshold: float, close: float | None, as_of: date | None) -> Observation | None:
    if close is None:
        return None
    met = close > threshold if alert_type == "price_above" else close < threshold
    side = "above" if alert_type == "price_above" else "below"
    label = f"${close:,.2f} on {as_of} ({'' if met else 'not '}{side} ${threshold:,.2f})"
    return Observation(value="met" if met else "not_met", label=label, detail=f"${close:,.2f} on {as_of}")


def observe_count(kind: str, count: int, latest: date | None) -> Observation:
    noun = "article" if kind == "news" else "filing"
    return Observation(value=str(count), label=f"{count:,} {noun}{'s' if count != 1 else ''}, latest {latest or '—'}",
                       detail=f"latest {latest}" if latest else "")


def decide(alert_type: str, ticker: str, threshold: float | None, previous: str | None, current: Observation) -> Decision:
    if alert_type in ("price_above", "price_below"):
        if current.value == "met" and previous != "met":
            side = "above" if alert_type == "price_above" else "below"
            return Decision(True, f"{ticker} closed {side} ${threshold:,.2f}: {current.detail}")
        return Decision(False)
    # news / filing: a growing count means something new arrived since last time
    if previous is None:
        return Decision(False)  # first look: record a baseline, don't alert on history
    new = int(current.value) - int(previous)
    if new > 0:
        noun = "news article" if alert_type == "news" else "SEC filing"
        return Decision(True, f"{new} new {noun}{'s' if new != 1 else ''} for {ticker} ({current.detail})")
    return Decision(False)


# ─── Observations from Postgres ──────────────────────────────────────────────

def _latest_close(ticker: str) -> tuple[float | None, date | None]:
    rows = query_dict(
        """
        SELECT "current" AS close, normalized_calendar_date::date AS day
        FROM staging_finnhub
        WHERE target_ticker = %s AND "current" IS NOT NULL
        ORDER BY normalized_calendar_date DESC, ingest_date DESC NULLS LAST
        LIMIT 1
        """,
        (ticker,),
    )
    return (float(rows[0]["close"]), rows[0]["day"]) if rows else (None, None)


def _news_count(ticker: str) -> tuple[int, date | None]:
    rows = query_dict(
        f"SELECT COUNT(*) AS n, MAX(normalized_calendar_date)::date AS latest FROM staging_gnews WHERE target_ticker = %s",
        (ticker,),
    )
    return int(rows[0]["n"]), rows[0]["latest"]


def _filing_count(ticker: str) -> tuple[int, date | None]:
    from app.services.vectorized_gcs import _cik_prefixes, _resolve_ticker_to_cik
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        return 0, None
    rows = query_dict(
        """
        SELECT COUNT(DISTINCT source_object) AS n, MAX(filing_date) AS latest
        FROM sec_vectorized_chunks
        WHERE source_object LIKE %s OR source_object LIKE %s
        """,
        _cik_prefixes(cik),
    )
    return int(rows[0]["n"]), rows[0]["latest"]


def observe(alert_type: str, ticker: str, threshold: float | None) -> Observation | None:
    if alert_type in ("price_above", "price_below"):
        close, as_of = _latest_close(ticker)
        return observe_price(alert_type, float(threshold), close, as_of)
    if alert_type == "news":
        return observe_count("news", *_news_count(ticker))
    if alert_type == "filing":
        return observe_count("filing", *_filing_count(ticker))
    return None


# ─── Runner ──────────────────────────────────────────────────────────────────

def evaluate_subscriptions(dry_run: bool = False) -> list[dict]:
    """Evaluate every active subscription once. Returns one result dict per subscription."""
    subs = query_dict(
        """
        SELECT s.id, s.user_id, s.ticker, s.alert_type, s.threshold, st.last_observed_value
        FROM alert_subscriptions s
        LEFT JOIN alert_subscription_state st ON st.subscription_id = s.id
        WHERE s.active
        ORDER BY s.id
        """
    )
    results = []
    for sub in subs:
        threshold = float(sub["threshold"]) if sub["threshold"] is not None else None
        current = observe(sub["alert_type"], sub["ticker"], threshold)
        if current is None:
            results.append({"id": sub["id"], "ticker": sub["ticker"], "type": sub["alert_type"], "status": "no data"})
            continue
        decision = decide(sub["alert_type"], sub["ticker"], threshold, sub["last_observed_value"], current)
        results.append({"id": sub["id"], "user_id": sub["user_id"], "ticker": sub["ticker"], "type": sub["alert_type"],
                        "previous": sub["last_observed_value"], "current": current.value, "label": current.label,
                        "fired": decision.fire, "message": decision.message})
        if dry_run:
            continue
        with get_connection() as conn:
            with conn.cursor() as cur:
                if decision.fire:
                    cur.execute(
                        """
                        INSERT INTO alerts (user_id, ticker, type, message, read, severity, created_at, subscription_id)
                        VALUES (%s, %s, %s, %s, FALSE, %s, NOW(), %s)
                        """,
                        (sub["user_id"], sub["ticker"], sub["alert_type"], decision.message,
                         SEVERITY.get(sub["alert_type"], "medium"), sub["id"]),
                    )
                cur.execute(
                    """
                    INSERT INTO alert_subscription_state (subscription_id, last_observed_value, last_observed_label,
                                                          last_evaluated_at, last_alerted_at)
                    VALUES (%s, %s, %s, NOW(), CASE WHEN %s THEN NOW() END)
                    ON CONFLICT (subscription_id) DO UPDATE SET
                        last_observed_value = EXCLUDED.last_observed_value,
                        last_observed_label = EXCLUDED.last_observed_label,
                        last_evaluated_at = EXCLUDED.last_evaluated_at,
                        last_alerted_at = COALESCE(EXCLUDED.last_alerted_at, alert_subscription_state.last_alerted_at)
                    """,
                    (sub["id"], current.value, current.label, decision.fire),
                )
            conn.commit()
    fired = sum(1 for r in results if r.get("fired"))
    logger.info("alert subscriptions evaluated: %d active, %d alert(s)%s", len(results), fired, " (dry run)" if dry_run else "")
    return results
