"""Extract fiscal year-end dates and period metadata from SEC filings."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from src.config import Settings
from src.error_logger import ErrorLogger
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient

logger = logging.getLogger(__name__)

# Visible text patterns (legacy format)
_FY_PATTERNS = [
    re.compile(r"Fiscal Year End:\s*([^\n<]+)", re.IGNORECASE),
    re.compile(r"Fiscal Year Ended.*?(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE | re.DOTALL),
]

# Inline XBRL patterns — uses DOTALL to handle nested tags
_IX_FY_PATTERN = re.compile(
    r'<ix:nonNumeric[^>]*name="dei:CurrentFiscalYearEndDate"[^>]*>(.*?)</ix:nonNumeric>',
    re.IGNORECASE | re.DOTALL,
)
_IX_YEAR_PATTERN = re.compile(
    r'<ix:nonNumeric[^>]*name="dei:DocumentFiscalYearFocus"[^>]*>(\d{4})</ix:nonNumeric>',
    re.IGNORECASE,
)
_IX_PERIOD_PATTERN = re.compile(
    r'<ix:nonNumeric[^>]*name="dei:DocumentPeriodEndDate"[^>]*>(.*?)</ix:nonNumeric>',
    re.IGNORECASE | re.DOTALL,
)


def _clean_html_value(value: str) -> str:
    return value.replace('&#160;', ' ').replace('&nbsp;', ' ').strip()


def _extract_fy_from_html(html: str) -> Optional[str]:
    # Try visible text patterns first
    for pattern in _FY_PATTERNS:
        match = pattern.search(html)
        if match:
            return match.group(1).strip()

    # Try inline XBRL pattern
    fy_match = _IX_FY_PATTERN.search(html)
    if fy_match:
        raw = fy_match.group(1)
        cleaned = _clean_html_value(re.sub(r'<[^>]+>', '', raw))
        year_match = _IX_YEAR_PATTERN.search(html)
        year = year_match.group(1) if year_match else None
        if year and cleaned:
            if cleaned.startswith("--"):
                return f"{year}-{cleaned[2:]}"
            else:
                return f"{cleaned} {year}"

        # Fallback: try DocumentPeriodEndDate for year
        if not year:
            period_match = _IX_PERIOD_PATTERN.search(html)
            if period_match:
                period_text = _clean_html_value(re.sub(r'<[^>]+>', '', period_match.group(1)))
                year_match = re.search(r"\b(\d{4})\b", period_text)
                if year_match:
                    year = year_match.group(1)
                    if cleaned.startswith("--"):
                        return f"{year}-{cleaned[2:]}"
                    else:
                        return f"{cleaned} {year}"

    return None


def _parse_fy_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    try:
        return pd.to_datetime(raw).strftime('%Y-%m-%d')
    except Exception:
        return None


def build_fiscal_parameters(settings: LakehouseSettings, sample: int | None = None) -> pd.DataFrame:
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    prefix = "SEC/10-K/"
    rows: list[dict] = []
    blobs = list(bucket.list_blobs(prefix=prefix))
    logger.info("Scanning %d 10-K blobs for fiscal year-end dates", len(blobs))

    for blob in blobs:
        if sample is not None and len(rows) >= sample:
            break
        if not blob.name.endswith(".htm") and not blob.name.endswith(".html"):
            continue
        parts = blob.name.split("/")
        if len(parts) < 5:
            continue
        cik = parts[2]
        accession_no_dashes = parts[3]
        accession = accession_no_dashes.replace("-", "")

        try:
            html = blob.download_as_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to download %s: %s", blob.name, exc)
            continue

        raw_fy = _extract_fy_from_html(html)
        if not raw_fy:
            logger.debug("No fiscal year-end found in %s", blob.name)
            continue

        iso_date = _parse_fy_date(raw_fy)
        if not iso_date:
            logger.warning("Could not parse fiscal year-end '%s' in %s", raw_fy, blob.name)
            continue

        rows.append(
            {
                "target_cik": cik,
                "fiscal_year_end_date": iso_date,
                "source_accession": accession,
                "extracted_at": pd.Timestamp.utcnow().isoformat(),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["target_cik", "source_accession"]).reset_index(drop=True)
    logger.info("Extracted fiscal year-end for %d companies", len(df))
    return df


def build_period_map(settings: LakehouseSettings) -> dict[str, dict[str, Optional[str]]]:
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    error_logger = ErrorLogger(settings.project_root / "error_log_period_map.txt")
    sec_client = SecClient(settings.sec_settings, error_logger)

    accession_map: dict[str, dict[str, Optional[str]]] = {}
    seen_ciks: set[str] = set()

    for prefix in ("SEC/8-K/", "SEC/10-K/"):
        blobs = list(bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            if not blob.name.endswith(".htm") and not blob.name.endswith(".html"):
                continue
            parts = blob.name.split("/")
            if len(parts) < 5:
                continue
            cik = parts[2]
            accession_no_dashes = parts[3]
            accession = accession_no_dashes.replace("-", "")
            if accession in accession_map:
                continue
            seen_ciks.add(cik)

    logger.info("Fetching submissions for %d unique CIKs", len(seen_ciks))
    for cik in seen_ciks:
        submissions = sec_client.get_submissions(cik)
        if not submissions:
            continue
        filings = submissions.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        periods = filings.get("periodOfReport", [])

        for idx, acc in enumerate(accessions):
            acc_clean = acc.replace("-", "") if acc else None
            if not acc_clean:
                continue
            period = periods[idx] if idx < len(periods) else None
            filing_date = filing_dates[idx] if idx < len(filing_dates) else None
            accession_map[acc_clean] = {
                "period_of_report": period,
                "filing_date": filing_date,
            }

    logger.info("Built period map for %d accessions", len(accession_map))
    return accession_map


def save_fiscal_parameters(df: pd.DataFrame, settings: LakehouseSettings) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = f"{settings.gcs_staging_prefix}/fiscal_parameters.parquet"
    table = pa.Table.from_pandas(df)
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    blob = bucket.blob(path)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
    logger.info("Saved fiscal parameters to gs://%s/%s", settings.gcs_bucket, path)
    return path
