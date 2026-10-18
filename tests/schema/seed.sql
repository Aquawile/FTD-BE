-- Seed rows for the throwaway db_integration database (tests/schema/setup_test_db.sh).
-- Synthetic values only: enough for every db_integration test to find data.
-- Dates cover 2024 (the range several older tests query) and Oct 2026 (live-like).

INSERT INTO tickers (symbol, name, sector, current_price, evidence_score, hype_score, change_percent, updated_at, price_as_of) VALUES
  ('AAPL', 'Apple Inc.',  'Technology',     340.00, 50, 50, 0.50, now(), '2026-10-15 20:00'),
  ('NVDA', 'NVIDIA Corp', 'Semiconductors', 214.13, 50, 50, -1.20, now(), '2026-10-16 20:00'),
  ('MSFT', 'Microsoft',   'Technology',     480.00, 50, 50, 0.10, now(), '2026-10-16 20:00');

-- Daily quotes (AAPL is a day behind in the snapshot above on purpose: the API must prefer the newer quote).
INSERT INTO staging_finnhub (target_ticker, target_cik, element_type, content_body, normalized_calendar_date,
                             ingest_date, symbol, "timestamp", "current", change, percent_change, high, low, open, previous_close)
SELECT s.sym, s.cik, 'quantitative', '', d::date, d::date + interval '22 hours', s.sym, d::date + interval '20 hours',
       s.base + extract(day FROM d)::numeric, 1.0, 0.5, s.base + 5, s.base - 5, s.base, s.base - 1
FROM (VALUES ('AAPL', '0000320193', 300.0), ('NVDA', '0001045810', 180.0), ('MSFT', '0000789019', 450.0)) AS s(sym, cik, base)
CROSS JOIN (
  SELECT generate_series('2024-06-03'::date, '2024-06-07'::date, interval '1 day') AS d
  UNION ALL
  SELECT generate_series('2026-10-12'::date, '2026-10-16'::date, interval '1 day')
) days;

INSERT INTO staging_gnews (target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, url) VALUES
  ('AAPL', '0000320193', 'narrative', 'Apple unveils new products at its June event.', '2024-06-10', '2024-06-11', 'https://example.com/aapl-2024-06-10'),
  ('AAPL', '0000320193', 'narrative', 'Apple shares rise after earnings.',              '2024-08-02', '2024-08-03', 'https://example.com/aapl-2024-08-02'),
  ('AAPL', '0000320193', 'narrative', 'Apple supplier news.',                           '2026-10-14', '2026-10-15', 'https://example.com/aapl-2026-10-14'),
  ('NVDA', '0001045810', 'narrative', 'NVIDIA data center demand stays strong.',        '2026-10-14', '2026-10-15', 'https://example.com/nvda-2026-10-14'),
  ('NVDA', '0001045810', 'narrative', 'NVIDIA announces new GPU.',                      '2026-10-15', '2026-10-16', 'https://example.com/nvda-2026-10-15');

-- Vectorized SEC mirror: one 10-K and one 8-K for AAPL, paths like SEC/{form}/{CIK}/{accession}/{ticker}-{date}.htm
INSERT INTO sec_vectorized_chunks (ticker, cik, accession_number, form_type, filing_date, chunk_index, text_preview,
                                   vector, source_bucket, source_object, vectorized_at) VALUES
  ('AAPL', '0000320193', '0000320193-26-000101', '10-K', '2026-06-22', 0, 'Annual report. Revenue grew.', '[]', 'raw-data-strg',
   'SEC/10-K/0000320193/000032019326000101/aapl-20260622.htm', '2026-10-15 00:10+00'),
  ('AAPL', '0000320193', '0000320193-26-000101', '10-K', '2026-06-22', 1, 'Risk factors include supply chain.', '[]', 'raw-data-strg',
   'SEC/10-K/0000320193/000032019326000101/aapl-20260622.htm', '2026-10-15 00:10+00'),
  ('AAPL', '0000320193', '0000320193-26-000202', '8-K', '2026-06-26', 0, 'Current report: dividend declared.', '[]', 'raw-data-strg',
   'SEC/8-K/0000320193/000032019326000202/aapl-20260626.htm', '2026-10-15 00:10+00');

INSERT INTO fiscal_parameters (target_cik, fiscal_year_end_date, source_accession, extracted_at) VALUES
  ('0000320193', '2025-09-27', '0000320193-26-000101', '2026-07-01');

INSERT INTO permissions (name, description) VALUES
  ('tickers.search', 'Search tickers'), ('tickers.prices', 'Read prices'), ('tickers.news', 'Read news'),
  ('tickers.filings', 'Read filings'), ('tickers.timeline', 'Read timelines'), ('tickers.fiscal_year_end', 'Read fiscal year end'),
  ('filings.read', 'Read filing elements'), ('search.read', 'Search content'), ('dashboard.read', 'Dashboard')
ON CONFLICT DO NOTHING;
