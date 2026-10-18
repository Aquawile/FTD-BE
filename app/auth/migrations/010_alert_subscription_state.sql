-- Migration 010: change tracking for alert subscriptions (additive only).
--
-- scripts/evaluate_alert_subscriptions.py runs at the end of each data sync. For
-- every active subscription it compares the value it observes now (latest close,
-- article count, filing count) with the last one recorded here, and inserts an
-- alert only when it changed. Nothing is deleted.

CREATE TABLE IF NOT EXISTS alert_subscription_state (
    subscription_id     INTEGER PRIMARY KEY REFERENCES alert_subscriptions(id),
    last_observed_value TEXT,
    last_observed_label TEXT,
    last_evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_alerted_at     TIMESTAMPTZ
);

-- Which subscription produced an alert (NULL for alerts from other sources).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS subscription_id INTEGER REFERENCES alert_subscriptions(id);
CREATE INDEX IF NOT EXISTS idx_alerts_subscription_id ON alerts(subscription_id);
