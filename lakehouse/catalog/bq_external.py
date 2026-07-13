"""Generate BigQuery external table DDL over lakehouse Parquet files."""

from __future__ import annotations

import logging
from pathlib import Path

from lakehouse.config import LakehouseSettings

logger = logging.getLogger(__name__)


_EXTERNAL_TABLE_DDL = {
    "staging_finnhub": """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.staging_finnhub`
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
  uris = ['gs://{bucket}/{prefix}/staging_finnhub.parquet']
);
""",
    "staging_gnews": """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.staging_gnews`
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
  uris = ['gs://{bucket}/{prefix}/staging_gnews.parquet']
);
""",
    "staging_sec": """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.staging_sec`
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
  uris = ['gs://{bucket}/{prefix}/staging_sec.parquet']
);
""",
    "unified_staging": """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.unified_staging`
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
  uris = ['gs://{bucket}/{prefix}/unified_staging.parquet']
);
""",
    "fiscal_parameters": """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.fiscal_parameters`
(
  target_cik STRING,
  fiscal_year_end_date STRING,
  source_accession STRING,
  extracted_at STRING
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://{bucket}/{prefix}/fiscal_parameters.parquet']
);
""",
}


def generate_external_table_ddl(settings: LakehouseSettings, project: str, dataset: str) -> str:
    statements = []
    for table_name, template in _EXTERNAL_TABLE_DDL.items():
        stmt = template.format(
            project=project,
            dataset=dataset,
            bucket=settings.gcs_bucket,
            prefix=settings.gcs_staging_prefix,
        ).strip()
        statements.append(stmt)
    return "\n\n".join(statements)


def write_external_table_ddl(settings: LakehouseSettings, project: str, dataset: str, output_path: Path | None = None) -> Path:
    ddl = generate_external_table_ddl(settings, project, dataset)
    if output_path is None:
        output_path = settings.project_root / "lakehouse" / "catalog" / "bq_external_tables.sql"
    output_path.write_text(ddl, encoding="utf-8")
    logger.info("Wrote BigQuery external table DDL to %s", output_path)
    return output_path
