"""Orchestrate the Option 1 lakehouse staging pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

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


def run_pipeline(project_root: Path | str, sample: int | None = None, postgres: bool = False, settings: LakehouseSettings | None = None) -> int:
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
    if postgres:
        if not settings.postgres_enabled:
            logger.error("PostgreSQL output requested but not configured in settings")
            return 1
        logger.info("PostgreSQL output enabled: %s@%s:%s/%s", settings.postgres_user, settings.postgres_host, settings.postgres_port, settings.postgres_db)

    tables = {
        "staging_finnhub": None,
        "staging_gnews": None,
        "staging_sec": None,
        "fiscal_parameters": None,
        "unified_staging": None,
    }

    # Track 1: SEC HTML DOM Shredder
    logger.info("=== Track 1: SEC Shredder ===")
    sec_df = process_sec_documents(settings, sample=sample)
    if sec_df.empty:
        logger.warning("No SEC elements extracted; skipping save.")
    else:
        save_sec_staging(sec_df, settings)
        tables["staging_sec"] = sec_df

    # Track 2: Finnhub Numerical Coercion
    logger.info("=== Track 2: Finnhub Coercion ===")
    prices_df = load_price_frames(settings, sample=sample)
    if prices_df.empty:
        logger.warning("No price rows loaded; skipping save.")
    else:
        save_price_staging(prices_df, settings)
        tables["staging_finnhub"] = prices_df

    # Track 3: GNews Normalizer
    logger.info("=== Track 3: GNews Normalizer ===")
    gnews_df = load_gnews_frames(settings, sample=sample)
    if gnews_df.empty:
        logger.warning("No GNews rows loaded; skipping save.")
    else:
        save_gnews_staging(gnews_df, settings)
        tables["staging_gnews"] = gnews_df

    # Fiscal Resolution Engine
    logger.info("=== Engine: Fiscal Resolver ===")
    fiscal_df = build_fiscal_parameters(settings, sample=sample)
    if fiscal_df.empty:
        logger.warning("No fiscal parameters extracted.")
    else:
        save_fiscal_parameters(fiscal_df, settings)
        tables["fiscal_parameters"] = fiscal_df

    # Validation Core
    logger.info("=== Engine: Validation Core ===")
    validated = validate_staging(settings, sample=sample)
    if not validated:
        logger.warning("No validated staging tables produced.")
    else:
        save_validated(validated, settings)
        for name in ("staging_finnhub", "staging_gnews", "staging_sec"):
            if name in validated:
                tables[name] = validated[name]

    # Unified staging
    logger.info("=== Engine: Unified Staging ===")
    unified = build_unified_staging(settings, sample=sample)
    if unified is None or unified.empty:
        logger.warning("No unified staging produced.")
    else:
        save_unified_staging(unified, settings)
        tables["unified_staging"] = unified

    # PostgreSQL output
    if postgres:
        logger.info("=== Writing to PostgreSQL ===")
        for table_name, df in tables.items():
            if table_name not in settings.postgres_tables:
                continue
            if df is None or df.empty:
                logger.warning("Skipping PostgreSQL write for %s: no data", table_name)
                continue
            truncate_table(settings, table_name)
            write_frame(settings, table_name, df)

    logger.info("Lakehouse staging pipeline complete.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run lakehouse staging pipeline")
    parser.add_argument("--sample", type=int, default=None, help="Limit each track to N items for fast testing")
    parser.add_argument("--postgres", action="store_true", help="Write output to PostgreSQL in addition to GCS")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    sys.exit(run_pipeline(project_root, sample=args.sample, postgres=args.postgres))
