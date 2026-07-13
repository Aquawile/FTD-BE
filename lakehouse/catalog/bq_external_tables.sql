CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_finnhub`
(
  target_ticker STRING,
  target_cik STRING,
  element_type STRING,
  content_body STRING,
  normalized_calendar_date TIMESTAMP,
  ingest_date TIMESTAMP,
  symbol STRING,
  `timestamp` TIMESTAMP,
  `current` BIGNUMERIC,
  change BIGNUMERIC,
  percent_change BIGNUMERIC,
  high BIGNUMERIC,
  low BIGNUMERIC,
  open BIGNUMERIC,
  previous_close BIGNUMERIC
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_finnhub.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_gnews`
(
  target_ticker STRING,
  target_cik STRING,
  element_type STRING,
  content_body STRING,
  normalized_calendar_date TIMESTAMP,
  ingest_date TIMESTAMP
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_gnews.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_sec`
(
  target_ticker STRING,
  target_cik STRING,
  element_type STRING,
  content_body STRING,
  normalized_calendar_date TIMESTAMP,
  ingest_date TIMESTAMP,
  element_id STRING,
  accession_number STRING,
  form_type STRING,
  item_number STRING,
  content_type STRING,
  raw_text_string STRING,
  period_of_report STRING,
  filing_date TIMESTAMP,
  date_precision STRING
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_sec.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.unified_staging`
(
  target_ticker STRING,
  target_cik STRING,
  element_type STRING,
  content_body STRING,
  normalized_calendar_date TIMESTAMP,
  ingest_date TIMESTAMP,
  symbol STRING,
  `timestamp` TIMESTAMP,
  `current` BIGNUMERIC,
  change BIGNUMERIC,
  percent_change BIGNUMERIC,
  high BIGNUMERIC,
  low BIGNUMERIC,
  open BIGNUMERIC,
  previous_close BIGNUMERIC,
  source STRING,
  form_type STRING,
  element_id STRING,
  accession_number STRING,
  item_number STRING,
  content_type STRING,
  raw_text_string STRING,
  period_of_report STRING,
  filing_date TIMESTAMP,
  date_precision STRING
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/unified_staging.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.fiscal_parameters`
(
  target_cik STRING,
  fiscal_year_end_date STRING,
  source_accession STRING,
  extracted_at STRING
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/fiscal_parameters.parquet']
);