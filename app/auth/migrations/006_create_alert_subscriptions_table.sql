CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    threshold NUMERIC,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_subscriptions_user_ticker_type
    ON alert_subscriptions(user_id, ticker, alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_user_id ON alert_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_ticker ON alert_subscriptions(ticker);

CREATE OR REPLACE FUNCTION update_alert_subscriptions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_alert_subscriptions_updated_at ON alert_subscriptions;

CREATE TRIGGER trg_update_alert_subscriptions_updated_at
    BEFORE UPDATE ON alert_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_alert_subscriptions_updated_at();
