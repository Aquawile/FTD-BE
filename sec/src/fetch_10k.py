"""One-time bootstrap: fetch 10-K filings for Fortune 500 CIKs and upload to GCS."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import Settings
from src.error_logger import ErrorLogger
from src.filing_fetcher import TenKFiling, extract_recent_10k_filings
from src.fortune500 import fetch_target_tickers
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient
from src.company_roster import fetch_ticker_cik_map, resolve_target_ciks

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)
    settings = Settings.from_env(PROJECT_ROOT)
    error_log_path = PROJECT_ROOT / "error_log_10k.txt"
    error_logger = ErrorLogger(error_log_path)

    try:
        settings.validate()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    sec_client = SecClient(settings, error_logger)
    storage = GcsStorage(settings)

    target_tickers = fetch_target_tickers(
        sec_client,
        storage,
        gcs_path=settings.fortune_500_gcs_path,
        fallback_url=settings.fortune_500_fallback_url,
        limit=settings.target_company_limit,
    )
    ticker_map = fetch_ticker_cik_map(sec_client, settings.company_tickers_url)
    ciks, missing_tickers = resolve_target_ciks(target_tickers, ticker_map)
    if missing_tickers:
        logger.warning(
            "No SEC CIK for %s target ticker(s): %s",
            len(missing_tickers),
            ", ".join(missing_tickers[:20]),
        )
    if not ciks:
        raise RuntimeError("No CIKs resolved for target ticker list")

    logger.info("Fetching 10-K filings for %s companies", len(ciks))

    total_uploaded = 0
    total_skipped = 0
    total_failed = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5

    for cik in ciks:
        submissions = sec_client.get_submissions(cik)
        if submissions is None:
            logger.warning("Failed to fetch submissions for CIK %s", cik)
            total_failed += 1
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    "Aborting 10-K bootstrap after %s consecutive failures. "
                    "Last failed CIK: %s. Check SEC API access and rate limits.",
                    consecutive_failures,
                    cik,
                )
                return 1
            continue

        filings = extract_recent_10k_filings(submissions, cik=cik)
        if not filings:
            logger.info("CIK %s: no 10-K filings found", cik)
            consecutive_failures = 0
            continue

        cik_uploaded = 0
        cik_skipped = 0
        for filing in filings:
            if storage.filing_exists(filing):
                cik_skipped += 1
                consecutive_failures = 0
                continue

            content = sec_client.download_document(
                filing.cik,
                filing.accession_number,
                filing.primary_document,
            )
            if content is None:
                total_failed += 1
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        "Aborting 10-K bootstrap after %s consecutive failures. "
                        "Last failed CIK: %s accession: %s. Check document access.",
                        consecutive_failures,
                        cik,
                        filing.accession_number,
                    )
                    return 1
                continue

            consecutive_failures = 0
            storage.upload_filing(filing, content)
            storage.upload_metadata(filing)
            cik_uploaded += 1

        total_uploaded += cik_uploaded
        total_skipped += cik_skipped
        logger.info(
            "CIK %s complete: uploaded=%s skipped_existing=%s",
            cik,
            cik_uploaded,
            cik_skipped,
        )

    if error_logger.has_entries():
        storage.upload_error_log(error_log_path)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_uploaded": total_uploaded,
        "total_skipped": total_skipped,
        "total_failed": total_failed,
        "ciks_processed": len(ciks),
    }
    storage.upload_config_blob(
        "SEC/logs/10k_bootstrap_manifest.json",
        json.dumps(manifest, indent=2).encode("utf-8"),
        content_type="application/json",
    )

    logger.info(
        "10-K bootstrap finished: uploaded=%s skipped_existing=%s failed=%s",
        total_uploaded,
        total_skipped,
        total_failed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
