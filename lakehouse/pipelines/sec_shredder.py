"""Shred SEC 8-K and 10-K HTML documents into structured element rows."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup, Comment
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from lakehouse.engines.validation_core import _coerce_schema
from src.config import Settings
from src.error_logger import ErrorLogger
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient
from lakehouse.engines.fiscal_resolver import build_period_map

logger = logging.getLogger(__name__)

_ITEM_HEADER_RE = re.compile(r"^\s*Item\s+\d+[A-Z]?\b", re.IGNORECASE)
_BOILERPLATE_RE = re.compile(
    r"UNITED STATES SECURITIES AND EXCHANGE COMMISSION|"
    r"WASHINGTON, D\.?C\.?|"
    r"Page \d+|"
    r"ANNUAL REPORT PURSUANT TO SECTION 13 OR 15\(d\)|"
    r"SECURITIES EXCHANGE ACT OF 1934|"
    r"FOR THE FISCAL YEAR ENDED|"
    r"^.*FILED WITH THE SECURITIES AND EXCHANGE COMMISSION.*$|"
    r"^.*COMMISSION FILE NUMBER.*$|"
    r"^\s*$",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if _BOILERPLATE_RE.search(line):
            continue
        line = line.strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _table_to_markdown(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [
            cell.get_text(strip=True)
            for cell in tr.find_all(["td", "th"])
        ]
        if not cells:
            continue
        rows.append("| " + " | ".join(cells) + " |")
        if len(rows) == 1:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


def _extract_item_number(text: str) -> Optional[str]:
    match = re.search(r"Item\s+(\d+[A-Z]?)", text, re.IGNORECASE)
    return match.group(1) if match else None


def shred_html(
    html: str,
    cik: str,
    accession: str,
    form_type: str,
    period_of_report: Optional[str] = None,
    filing_date: Optional[str] = None,
) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    rows: list[dict] = []
    current_item: Optional[str] = None
    current_content_type: str = "unknown"

    for element in soup.find_all(
        ["p", "div", "table", "b", "strong", "h1", "h2", "h3", "h4"]
    ):
        tag = element.name
        text = element.get_text(separator=" ", strip=True)
        if not text:
            continue

        if tag in ("b", "strong", "h1", "h2", "h3", "h4"):
            if _ITEM_HEADER_RE.match(text):
                current_item = _extract_item_number(text)
                current_content_type = text.split(".")[-1].strip() if "." in text else "general"
                continue

        if tag == "table":
            content_body = _table_to_markdown(element)
            element_type = "quantitative"
            if not content_body.strip():
                continue
        else:
            content_body = _clean_text(text)
            element_type = "narrative"
            if len(content_body) < 40:
                continue

        rows.append(
            {
                "element_id": str(uuid.uuid4()),
                "target_cik": cik,
                "accession_number": accession,
                "form_type": form_type,
                "item_number": current_item,
                "content_type": current_content_type,
                "element_type": element_type,
                "raw_text_string": content_body[:1000],
                "content_body": content_body,
                "period_of_report": period_of_report or "",
                "filing_date": filing_date or "",
                "normalized_calendar_date": None,
                "ingest_date": pd.Timestamp.utcnow().date().isoformat(),
            }
        )

    df = pd.DataFrame(rows)
    logger.debug("Shredded %d elements from %s", len(df), accession)
    return df


def process_sec_documents(settings: LakehouseSettings, sample: int | None = None) -> pd.DataFrame:
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    period_map = build_period_map(settings)
    frames: list[pd.DataFrame] = []
    total_processed = 0

    for form_type, gcs_prefix in (
        ("8-K", "SEC/8-K/"),
        ("10-K", "SEC/10-K/"),
    ):
        if sample is not None and total_processed >= sample:
            break
        blobs = list(bucket.list_blobs(prefix=gcs_prefix))
        logger.info("Found %d blobs for %s", len(blobs), form_type)
        for blob in blobs:
            if sample is not None and total_processed >= sample:
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

            meta = period_map.get(accession, {})
            df = shred_html(
                html,
                cik=cik,
                accession=accession,
                form_type=form_type,
                period_of_report=meta.get("period_of_report"),
                filing_date=meta.get("filing_date"),
            )
            if not df.empty:
                frames.append(df)
                total_processed += 1

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def save_sec_staging(df: pd.DataFrame, settings: LakehouseSettings) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = f"{settings.gcs_staging_prefix}/staging_sec.parquet"
    df = _coerce_schema(df)
    table = pa.Table.from_pandas(df, preserve_index=False)
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    blob = bucket.blob(path)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
    logger.info("Saved %d SEC elements to gs://%s/%s", len(df), settings.gcs_bucket, path)
    return path
