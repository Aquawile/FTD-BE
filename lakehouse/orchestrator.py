"""Orchestrate the Option 1 lakehouse staging pipeline."""

from __future__ import annotations

import argparse
import gc
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from lakehouse.engines.fiscal_resolver import build_fiscal_parameters, save_fiscal_parameters
from lakehouse.engines.postgres_writer import truncate_table, write_frame
from lakehouse.engines.unified_staging import build_unified_staging, save_unified_staging
from lakehouse.engines.validation_core import save_validated, validate_staging
from lakehouse.pipelines.finnhub_coercion import load_price_frames, save_price_staging
from lakehouse.pipelines.gnews_normalizer import load_gnews_frames, save_gnews_staging
from lakehouse.pipelines.sec_shredder import process_sec_documents, save_sec_staging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# The live staging tables are maintained incrementally by scripts/sync_all_recent.sh.
# This writer TRUNCATEs a table and rewrites only the current run's window, which
# wiped history and reintroduced duplicate/misattributed rows (CLAUDE.md known
# issues #8-#10). It is disabled unless explicitly re-enabled for a one-off rebuild.
_ALLOW_POSTGRES_TRUNCATE = os.getenv("LAKEHOUSE_ALLOW_POSTGRES_TRUNCATE") == "1"


def _write_table_to_postgres(settings: LakehouseSettings, table_name: str, df) -> None:
    if table_name not in settings.postgres_tables:
        return
    if not _ALLOW_POSTGRES_TRUNCATE:
        logger.warning(
            "Skipping PostgreSQL write for %s: truncate+rewrite is disabled "
            "(set LAKEHOUSE_ALLOW_POSTGRES_TRUNCATE=1 for a deliberate rebuild)", table_name)
        return
    if df is None or df.empty:
        logger.warning("Skipping PostgreSQL write for %s: no data", table_name)
        return
    truncate_table(settings, table_name)
    write_frame(settings, table_name, df)
    logger.info("Wrote %s to PostgreSQL", table_name)


def run_pipeline(project_root: Path | str, sample: int | None = None, postgres: bool = False, settings: LakehouseSettings | None = None, since: str | None = None) -> int:
    if settings is None:
        settings = LakehouseSettings.from_project_root(project_root)
    if postgres:
        import os
        if not settings.postgres_host:
            settings.postgres_host = os.getenv("PGHOST", "")
        if not settings.postgres_port:
            settings.postgres_port = int(os.getenv("PGPORT", "5432"))
        if not settings.postgres_db:
            settings.postgres_db = os.getenv("PGDATABASE", "")
        if not settings.postgres_user:
            settings.postgres_user = os.getenv("PGUSER", "")
        if not settings.postgres_password:
            settings.postgres_password = os.getenv("PGPASSWORD", "")
        if not settings.postgres_tables:
            settings.postgres_tables = ("staging_finnhub", "staging_gnews", "staging_sec", "unified_staging", "fiscal_parameters")
    logger.info("Lakehouse project root: %s", settings.project_root)
    if sample:
        logger.info("Sample mode: processing at most %d items per track", sample)
    if since:
        logger.info("Incremental mode: processing data since %s", since)
    if postgres:
        if not settings.postgres_enabled:
            logger.error("PostgreSQL output requested but not configured in settings")
            return 1
        logger.info("PostgreSQL output enabled: %s@%s:%s/%s", settings.postgres_user, settings.postgres_host, settings.postgres_port, settings.postgres_db)

    # Track 1: Finnhub Numerical Coercion (fast)
    logger.info("=== Track 1: Finnhub Coercion ===")
    prices_df = load_price_frames(settings, sample=sample, since=since)
    if prices_df.empty:
        logger.warning("No price rows loaded; skipping save.")
    else:
        save_price_staging(prices_df, settings)
        _write_table_to_postgres(settings, "staging_finnhub", prices_df)
        del prices_df
        gc.collect()

    # Track 2: GNews Normalizer (fast)
    logger.info("=== Track 2: GNews Normalizer ===")
    gnews_df = load_gnews_frames(settings, sample=sample, since=since)
    if gnews_df.empty:
        logger.warning("No GNews rows loaded; skipping save.")
    else:
        save_gnews_staging(gnews_df, settings)
        _write_table_to_postgres(settings, "staging_gnews", gnews_df)
        del gnews_df
        gc.collect()

    # Track 3: SEC HTML DOM Shredder (slow)
    logger.info("=== Track 3: SEC Shredder ===")
    sec_df = process_sec_documents(settings, sample=sample, since=since)
    if sec_df.empty:
        logger.warning("No SEC elements extracted; skipping save.")
    else:
        save_sec_staging(sec_df, settings)
        _write_table_to_postgres(settings, "staging_sec", sec_df)
        del sec_df
        gc.collect()

    # Fiscal Resolution Engine
    logger.info("=== Engine: Fiscal Resolver ===")
    fiscal_df = build_fiscal_parameters(settings, sample=sample, since=since)
    if fiscal_df.empty:
        logger.warning("No fiscal parameters extracted.")
    else:
        save_fiscal_parameters(fiscal_df, settings)
        _write_table_to_postgres(settings, "fiscal_parameters", fiscal_df)
        del fiscal_df
        gc.collect()

    # Validation Core - process and write one table at a time
    logger.info("=== Engine: Validation Core ===")
    cik_map = None
    fiscal_map = None
    from lakehouse.engines.validation_core import _build_cik_map as _build_cik, _load_fiscal_map as _load_fiscal
    cik_map = _build_cik(settings)
    fiscal_map = _load_fiscal(settings)

    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)

    for table_name in ("staging_finnhub", "staging_gnews", "staging_sec"):
        path = f"{settings.gcs_staging_prefix}/{table_name}.parquet"
        blob = bucket.blob(path)
        if not blob.exists():
            logger.warning("Staging table %s not found", path)
            continue
        buf = blob.download_as_bytes()
        table = pq.read_table(pa.BufferReader(buf))
        df = table.to_pandas()

        # Fortune 500 filter
        df = df[df["target_cik"].isin(cik_map.values())].copy()

        # Backfill target_ticker from inverse CIK map
        from lakehouse.engines.validation_core import _backfill_target_ticker
        df = _backfill_target_ticker(df, cik_map)

        # Ensure ingest_date exists
        if "ingest_date" not in df.columns:
            df["ingest_date"] = pd.Timestamp.utcnow().date().isoformat()

        # SEC-specific fiscal date enrichment
        if table_name == "staging_sec":
            from lakehouse.engines.validation_core import _enrich_sec_dates
            df = _enrich_sec_dates(df, fiscal_map)

        # Ensure canonical columns exist
        from lakehouse.engines.validation_core import _CANONICAL_COLUMNS, _coerce_schema
        for col in _CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        # Coerce schema
        df = _coerce_schema(df)

        # Reorder columns
        canonical = [c for c in _CANONICAL_COLUMNS if c in df.columns]
        extras = [c for c in df.columns if c not in _CANONICAL_COLUMNS]
        df = df[canonical + extras].reset_index(drop=True)

        # Sample if requested
        if sample is not None and len(df) > sample:
            df = df.sample(n=sample, random_state=42).reset_index(drop=True)

        logger.info("Validated %s: %d rows, columns=%s", table_name, len(df), list(df.columns))

        # Save validated table
        save_validated({table_name: df}, settings)

        # Write to PostgreSQL immediately
        _write_table_to_postgres(settings, table_name, df)

        # Free memory
        del df, table
        gc.collect()

    # Unified staging
    logger.info("=== Engine: Unified Staging ===")
    unified = build_unified_staging(settings, sample=sample, since=since)
    if unified is None or unified.empty:
        logger.warning("No unified staging produced.")
    else:
        save_unified_staging(unified, settings)
        _write_table_to_postgres(settings, "unified_staging", unified)
        del unified
        gc.collect()

    logger.info("Lakehouse staging pipeline complete.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run lakehouse staging pipeline")
    parser.add_argument("--sample", type=int, default=None, help="Limit each track to N items for fast testing")
    parser.add_argument("--postgres", action="store_true", help="Write output to PostgreSQL in addition to GCS")
    parser.add_argument("--since", type=str, default=None, help="Process only data newer than this date (ISO format)")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    sys.exit(run_pipeline(project_root, sample=args.sample, postgres=args.postgres, since=args.since))
