"""Generate BigQuery external table DDL over lakehouse Parquet files."""

from __future__ import annotations

import logging
from pathlib import Path

from lakehouse.config import LakehouseSettings

logger = logging.getLogger(__name__)


_EXTERNAL_TABLE_DDL = """
CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.{table}`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://{bucket}/{prefix}/{file}']
);
"""

_TABLES = [
    ("staging_finnhub", "staging_finnhub.parquet"),
    ("staging_gnews", "staging_gnews.parquet"),
    ("staging_sec", "staging_sec.parquet"),
    ("unified_staging", "unified_staging.parquet"),
    ("fiscal_parameters", "fiscal_parameters.parquet"),
]


def generate_external_table_ddl(settings: LakehouseSettings, project: str, dataset: str) -> str:
    statements = []
    for table_name, file_name in _TABLES:
        stmt = _EXTERNAL_TABLE_DDL.format(
            project=project,
            dataset=dataset,
            table=table_name,
            bucket=settings.gcs_bucket,
            prefix=settings.gcs_staging_prefix,
            file=file_name,
        )
        statements.append(stmt.strip())
    return "\n\n".join(statements)


def write_external_table_ddl(settings: LakehouseSettings, project: str, dataset: str, output_path: Path | None = None) -> Path:
    ddl = generate_external_table_ddl(settings, project, dataset)
    if output_path is None:
        output_path = settings.project_root / "lakehouse" / "catalog" / "bq_external_tables.sql"
    output_path.write_text(ddl, encoding="utf-8")
    logger.info("Wrote BigQuery external table DDL to %s", output_path)
    return output_path
