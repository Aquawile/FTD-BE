CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_finnhub`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_finnhub.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_gnews`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_gnews.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.staging_sec`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/staging_sec.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.unified_staging`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/unified_staging.parquet']
);

CREATE OR REPLACE EXTERNAL TABLE `ftd2026.lakehouse.fiscal_parameters`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://raw-data-strg/lakehouse/staging/fiscal_parameters.parquet']
);