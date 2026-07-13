CREATE OR REPLACE VIEW `ftd2026.lakehouse.prices_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  current,
  change,
  percent_change,
  high,
  low,
  open,
  previous_close,
  normalized_calendar_date,
  ingest_date
FROM `ftd2026.lakehouse.staging_finnhub`;

CREATE OR REPLACE VIEW `ftd2026.lakehouse.sentiment_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  normalized_calendar_date,
  ingest_date
FROM `ftd2026.lakehouse.staging_gnews`;

CREATE OR REPLACE VIEW `ftd2026.lakehouse.sec_elements_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  form_type,
  item_number,
  accession_number,
  period_of_report,
  filing_date,
  normalized_calendar_date,
  ingest_date
FROM `ftd2026.lakehouse.staging_sec`;

CREATE OR REPLACE VIEW `ftd2026.lakehouse.unified_financials` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  normalized_calendar_date,
  ingest_date,
  source,
  form_type
FROM `ftd2026.lakehouse.unified_staging`;