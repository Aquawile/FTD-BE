"""Per-CIK delta scanning via the SEC Submissions API.

Daily cron jobs query https://data.sec.gov/submissions/CIK##########.json for each
ticker-resolved CIK and only process 8-K filings whose filingDate falls within the
configured lookback window (24 hours in steady state, 7 days on initial backfill).
"""

from __future__ import annotations

import logging
from typing import Any

from src.filing_fetcher import EightKFiling, extract_recent_8k_filings
from src.sec_client import SecClient

logger = logging.getLogger(__name__)


def delta_scan_cik(
    cik: str,
    *,
    sec_client: SecClient,
    lookback_days: int,
) -> tuple[dict[str, Any] | None, list[EightKFiling]]:
    """Fetch one company's submissions JSON and return eligible 8-K filings."""
    submissions = sec_client.get_submissions(cik)
    if submissions is None:
        return None, []

    filings = extract_recent_8k_filings(
        submissions,
        cik=cik,
        lookback_days=lookback_days,
    )
    return submissions, filings


def run_delta_scan(
    ciks: list[str],
    *,
    sec_client: SecClient,
    lookback_days: int,
) -> dict[str, list[EightKFiling]]:
    """Scan each CIK independently; returns only CIKs with filings in the window."""
    results: dict[str, list[EightKFiling]] = {}
    for cik in ciks:
        _, filings = delta_scan_cik(
            cik,
            sec_client=sec_client,
            lookback_days=lookback_days,
        )
        if filings:
            results[cik] = filings
            logger.info(
                "Delta-scan CIK %s: %s 8-K filing(s) within %s-day window",
                cik,
                len(filings),
                lookback_days,
            )
    return results
