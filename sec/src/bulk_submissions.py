"""Download and parse the SEC bulk submissions.zip archive.

Reserved for full audit / system refresh only — not used by the daily delta-scan cron.
"""

from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from src.config import Settings
from src.sec_client import SecClient

logger = logging.getLogger(__name__)

BULK_SUBMISSIONS_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
)


def download_bulk_submissions(
    sec_client: SecClient,
    settings: Settings,
    destination: Path,
) -> bool:
    max_bytes = settings.max_download_bytes
    logger.info(
        "Downloading bulk submissions archive (limit %.2f GB)",
        max_bytes / (1024 ** 3),
    )
    return sec_client.download_to_file(
        BULK_SUBMISSIONS_URL,
        destination,
        cik="BULK",
        max_bytes=max_bytes,
    )


def extract_submissions_for_ciks(
    zip_path: Path,
    target_ciks: set[str],
) -> dict[str, dict[str, Any]]:
    submissions: dict[str, dict[str, Any]] = {}
    prefix_lookup = {f"CIK{cik}.json" for cik in target_ciks}

    with zipfile.ZipFile(zip_path, "r") as archive:
        available = set(archive.namelist())
        for member in prefix_lookup:
            if member not in available:
                basename = member.split("/")[-1]
                matches = [name for name in available if name.endswith(basename)]
                if not matches:
                    logger.warning("No bulk submission entry found for %s", member)
                    continue
                member = matches[0]

            raw = archive.read(member)
            payload = json.loads(raw)
            cik = SecClient.normalize_cik(str(payload.get("cik", member[3:13])))
            submissions[cik] = payload

    logger.info(
        "Loaded %s/%s submission records from bulk archive",
        len(submissions),
        len(target_ciks),
    )
    return submissions
