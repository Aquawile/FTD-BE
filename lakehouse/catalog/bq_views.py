"""Generate BigQuery view definitions over lakehouse external tables."""

from __future__ import annotations

import logging
from pathlib import Path

from lakehouse.config import LakehouseSettings

logger = logging.getLogger(__name__)


_VIEWS = {
    "prices_mart": """
CREATE OR REPLACE VIEW `{project}.{dataset}.prices_mart` AS
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
FROM `{project}.lakehouse.staging_finnhub`;
""",
    "sentiment_mart": """
CREATE OR REPLACE VIEW `{project}.{dataset}.sentiment_mart` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date
FROM `{project}.lakehouse.staging_gnews`;
""",
    "sec_elements_mart": """
CREATE OR REPLACE VIEW `{project}.{dataset}.sec_elements_mart` AS
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
FROM `{project}.lakehouse.staging_sec`;
""",
    "unified_financials": """
CREATE OR REPLACE VIEW `{project}.{dataset}.unified_financials` AS
SELECT
  target_ticker,
  target_cik,
  element_type,
  content_body,
  DATE(normalized_calendar_date) AS normalized_calendar_date,
  ingest_date,
  source,
  form_type
FROM `{project}.lakehouse.unified_staging`;
""",
}


def generate_view_ddl(settings: LakehouseSettings, project: str, dataset: str) -> str:
    statements = []
    for view_name, template in _VIEWS.items():
        stmt = template.format(project=project, dataset=dataset).strip()
        statements.append(stmt)
    return "\n\n".join(statements)


def write_view_ddl(settings: LakehouseSettings, project: str, dataset: str, output_path: Path | None = None) -> Path:
    ddl = generate_view_ddl(settings, project, dataset)
    if output_path is None:
        output_path = settings.project_root / "lakehouse" / "catalog" / "bq_views.sql"
    output_path.write_text(ddl, encoding="utf-8")
    logger.info("Wrote BigQuery view DDL to %s", output_path)
    return output_path
