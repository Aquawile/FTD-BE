"""SEC Form 8-K ingestion pipeline entry point."""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

from src.bulk_submissions import (
    download_bulk_submissions,
    extract_submissions_for_ciks,
)
from src.config import Settings
from src.delta_scan import delta_scan_cik
from src.error_logger import ErrorLogger
from src.filing_fetcher import EightKFiling, extract_recent_8k_filings
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient
from src.company_roster import fetch_ticker_cik_map, resolve_target_ciks
from src.fortune500 import fetch_target_tickers
from src.vm_lifecycle import is_running_on_gcp, stop_vm

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def ingest_filings(
    filings: list[EightKFiling],
    *,
    sec_client: SecClient,
    storage: GcsStorage,
) -> tuple[int, int]:
    uploaded = 0
    skipped = 0
    for filing in filings:
        if storage.filing_exists(filing):
            skipped += 1
            continue

        content = sec_client.download_document(
            filing.cik,
            filing.accession_number,
            filing.primary_document,
        )
        if content is None:
            continue

        storage.upload_filing(filing, content)
        storage.upload_metadata(filing)
        uploaded += 1

    return uploaded, skipped


def run_delta_scan_pipeline(
    ciks: list[str],
    *,
    sec_client: SecClient,
    storage: GcsStorage,
    lookback_days: int,
) -> tuple[int, int]:
    """Per-CIK Submissions API delta-scan (default daily mode)."""
    logger = logging.getLogger(__name__)
    total_uploaded = 0
    total_skipped = 0

    for cik in ciks:
        _, filings = delta_scan_cik(
            cik,
            sec_client=sec_client,
            lookback_days=lookback_days,
        )
        if not filings:
            continue

        uploaded, skipped = ingest_filings(
            filings,
            sec_client=sec_client,
            storage=storage,
        )
        total_uploaded += uploaded
        total_skipped += skipped
        logger.info(
            "CIK %s complete: uploaded=%s skipped_existing=%s",
            cik,
            uploaded,
            skipped,
        )

    return total_uploaded, total_skipped


def run_bulk_refresh_pipeline(
    ciks: list[str],
    *,
    settings: Settings,
    sec_client: SecClient,
    storage: GcsStorage,
    lookback_days: int,
) -> tuple[int, int]:
    """Full audit via submissions.zip — use only for system refresh, not daily cron."""
    logger = logging.getLogger(__name__)
    target = set(ciks)
    total_uploaded = 0
    total_skipped = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "submissions.zip"
        if not download_bulk_submissions(sec_client, settings, zip_path):
            logger.error("Bulk archive download failed; aborting full refresh")
            return 0, 0

        submissions_map = extract_submissions_for_ciks(zip_path, target)

    for cik in ciks:
        submissions = submissions_map.get(cik)
        if submissions is None:
            logger.warning("No bulk submission record for CIK %s", cik)
            continue

        filings = extract_recent_8k_filings(
            submissions,
            cik=cik,
            lookback_days=lookback_days,
        )
        uploaded, skipped = ingest_filings(
            filings,
            sec_client=sec_client,
            storage=storage,
        )
        total_uploaded += uploaded
        total_skipped += skipped
        logger.info(
            "CIK %s complete: uploaded=%s skipped_existing=%s",
            cik,
            uploaded,
            skipped,
        )

    return total_uploaded, total_skipped


def run_pipeline(settings: Settings, error_log_path: Path) -> int:
    logger = logging.getLogger(__name__)
    error_logger = ErrorLogger(error_log_path)
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

    previous_roster = storage.load_roster_manifest()
    added = sorted(set(target_tickers) - (previous_roster or set()))
    removed = sorted((previous_roster or set()) - set(target_tickers))
    if added:
        logger.info("Roster additions (%s): %s", len(added), ", ".join(added[:20]))
    if removed:
        logger.info("Roster removals (%s): %s", len(removed), ", ".join(removed[:20]))
    storage.save_roster_manifest(target_tickers)

    initial_run_complete = storage.has_completed_initial_run()
    lookback_days = settings.resolve_lookback_days(initial_run_complete)
    mode = "bulk-refresh" if settings.use_bulk_submissions else "delta-scan"
    logger.info(
        "Starting SEC 8-K ingestion for %s companies "
        "(%s-day lookback, mode=%s)",
        len(ciks),
        lookback_days,
        mode,
    )

    if settings.use_bulk_submissions:
        total_uploaded, total_skipped = run_bulk_refresh_pipeline(
            ciks,
            settings=settings,
            sec_client=sec_client,
            storage=storage,
            lookback_days=lookback_days,
        )
    else:
        total_uploaded, total_skipped = run_delta_scan_pipeline(
            ciks,
            sec_client=sec_client,
            storage=storage,
            lookback_days=lookback_days,
        )

    if not initial_run_complete:
        manifest_uri = storage.mark_initial_run_complete(
            uploaded=total_uploaded,
            skipped=total_skipped,
        )
        logger.info("Recorded initial run manifest at %s", manifest_uri)

    if error_logger.has_entries():
        gcs_uri = storage.upload_error_log(error_log_path)
        logger.warning("Uploaded error log to %s", gcs_uri)
    else:
        logger.info("No errors recorded during ingestion")

    logger.info(
        "Ingestion finished: uploaded=%s skipped_existing=%s bytes_transferred=%.2f MB",
        total_uploaded,
        total_skipped,
        sec_client.bytes_transferred / (1024 * 1024),
    )
    return 0


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)
    settings = Settings.from_env(PROJECT_ROOT)
    error_log_path = PROJECT_ROOT / settings.error_log_filename

    try:
        settings.validate()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if not settings.allow_local_execution and not is_running_on_gcp():
        logger.error(
            "Refusing to run outside GCP. Set ALLOW_LOCAL_EXECUTION=true only "
            "for controlled debugging."
        )
        return 1

    exit_code = 1
    try:
        exit_code = run_pipeline(settings, error_log_path)
    except Exception:
        logger.exception("Unhandled pipeline failure")
        exit_code = 1
    finally:
        stop_vm(settings)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
