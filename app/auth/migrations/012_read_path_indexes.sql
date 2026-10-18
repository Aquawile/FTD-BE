-- 012: indexes for the read paths the app uses on every request. No rows change.
--   staging_finnhub: latest quote per ticker (/tickers/tracked) and per-ticker prices
--   staging_gnews:   per-ticker news paging, and the distinct-article count (dashboard)
--   staging_sec_archive: distinct SEC filings for the dashboard count (archive is paused, never deleted)
CREATE INDEX IF NOT EXISTS idx_staging_finnhub_ticker_date
    ON staging_finnhub (target_ticker, normalized_calendar_date DESC, ingest_date DESC);
CREATE INDEX IF NOT EXISTS idx_staging_gnews_ticker_date
    ON staging_gnews (target_ticker, normalized_calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_staging_gnews_url
    ON staging_gnews (url);
CREATE INDEX IF NOT EXISTS idx_staging_sec_archive_accession
    ON staging_sec_archive (accession_number);
