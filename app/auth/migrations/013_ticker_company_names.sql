-- 013: company display names per ticker, from each company's latest 10-K
-- (gs://raw-data-strg/SEC/config/company_names.json, loaded by scripts/load_company_names.py).
-- Separate from tickers so tickers.name is never overwritten; the API shows
-- tickers.name when it is a real name, else this, else the symbol. Insert-only.
CREATE TABLE IF NOT EXISTS ticker_company_names (
    symbol       TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    source       TEXT,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
GRANT SELECT, INSERT ON ticker_company_names TO ftd_app;
