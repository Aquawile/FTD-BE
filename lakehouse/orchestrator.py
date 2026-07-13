"""Orchestrate the Option 1 lakehouse staging pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from lakehouse.config import LakehouseSettings
from lakehouse.engines.fiscal_resolver import build_fiscal_parameters, save_fiscal_parameters
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


def run_pipeline(project_root: Path | str, sample: int | None = None) -> int:
    settings = LakehouseSettings.from_project_root(project_root)
    logger.info("Lakehouse project root: %s", settings.project_root)
    if sample:
        logger.info("Sample mode: processing at most %d items per track", sample)

    # Track 1: SEC HTML DOM Shredder
    logger.info("=== Track 1: SEC Shredder ===")
    sec_df = process_sec_documents(settings, sample=sample)
    if sec_df.empty:
        logger.warning("No SEC elements extracted; skipping save.")
    else:
        save_sec_staging(sec_df, settings)

    # Track 2: Finnhub Numerical Coercion
    logger.info("=== Track 2: Finnhub Coercion ===")
    prices_df = load_price_frames(settings, sample=sample)
    if prices_df.empty:
        logger.warning("No price rows loaded; skipping save.")
    else:
        save_price_staging(prices_df, settings)

    # Track 3: GNews Normalizer
    logger.info("=== Track 3: GNews Normalizer ===")
    gnews_df = load_gnews_frames(settings, sample=sample)
    if gnews_df.empty:
        logger.warning("No GNews rows loaded; skipping save.")
    else:
        save_gnews_staging(gnews_df, settings)

    # Fiscal Resolution Engine
    logger.info("=== Engine: Fiscal Resolver ===")
    fiscal_df = build_fiscal_parameters(settings, sample=sample)
    if fiscal_df.empty:
        logger.warning("No fiscal parameters extracted.")
    else:
        save_fiscal_parameters(fiscal_df, settings)

    # Validation Core
    logger.info("=== Engine: Validation Core ===")
    validated = validate_staging(settings)
    if not validated:
        logger.warning("No validated staging tables produced.")
    else:
        save_validated(validated, settings)

    # Unified staging
    logger.info("=== Engine: Unified Staging ===")
    unified = build_unified_staging(settings)
    if unified is None or unified.empty:
        logger.warning("No unified staging produced.")
    else:
        save_unified_staging(unified, settings)

    logger.info("Lakehouse staging pipeline complete.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run lakehouse staging pipeline")
    parser.add_argument("--sample", type=int, default=None, help="Limit each track to N items for fast testing")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    sys.exit(run_pipeline(project_root, sample=args.sample))
