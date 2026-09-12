CREATE OR REPLACE VIEW `ftd2026.analytics.prices_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  `current`,
  change,
  percent_change,
  high,
  low,
  open,
  previous_close,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date
FROM `ftd2026.lakehouse.staging_finnhub`;

CREATE OR REPLACE VIEW `ftd2026.analytics.sentiment_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date,
  url
FROM `ftd2026.lakehouse.staging_gnews`;

CREATE OR REPLACE VIEW `ftd2026.analytics.sec_elements_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  form_type,
  item_number,
  accession_number,
  period_of_report,
  DATE(filing_date) AS filing_date,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date
FROM `ftd2026.lakehouse.staging_sec`;

CREATE OR REPLACE VIEW `ftd2026.analytics.unified_financials` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date,
  source,
  form_type,
  url
FROM `ftd2026.lakehouse.unified_staging`;