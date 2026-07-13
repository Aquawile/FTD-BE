"""Coerce Finnhub price JSON streams into structured staging DataFrames."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

import pandas as pd
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from lakehouse.engines.validation_core import _coerce_schema
from src.config import Settings
from src.error_logger import ErrorLogger
from src.fortune500 import fetch_target_tickers
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient

logger = logging.getLogger(__name__)

_NUMERIC_FIELDS = (
    "current",
    "change",
    "percent_change",
    "high",
    "low",
    "open",
    "previous_close",
)


def _iter_price_blobs(settings: LakehouseSettings) -> Iterator[storage.Blob]:
    """Yield price NDJSON blobs from GCS."""
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    prefix = "prices/"
    yield from bucket.list_blobs(prefix=prefix)


def _parse_price_line(line: str) -> dict:
    """Parse a single NDJSON line into a dict with explicit numeric coercion."""
    record = json.loads(line)
    parsed: dict = {}
    for key in (
        "symbol",
        "timestamp",
        "current",
        "change",
        "percent_change",
        "high",
        "low",
        "open",
        "previous_close",
    ):
        value = record.get(key)
        if key == "timestamp":
            parsed[key] = value
        elif key in _NUMERIC_FIELDS:
            try:
                parsed[key] = Decimal(str(value)) if value is not None else None
            except (InvalidOperation, ValueError):
                parsed[key] = None
        else:
            parsed[key] = value
    return parsed


def load_price_frames(settings: LakehouseSettings, sample: int | None = None) -> pd.DataFrame:
    """Load all price NDJSON blobs into a single DataFrame.

    Adds target_ticker, target_cik, element_type, and normalized_calendar_date.
    Skips records with null timestamp or null current price.
    """
    sec_settings = settings.sec_settings
    storage = GcsStorage(sec_settings)
    error_logger = ErrorLogger(settings.project_root / "error_log_finnhub.txt")
    sec_client = SecClient(sec_settings, error_logger)

    target_tickers = fetch_target_tickers(
        sec_client,
        storage,
        gcs_path=sec_settings.fortune_500_gcs_path,
        fallback_url=sec_settings.fortune_500_fallback_url,
        limit=settings.target_company_limit,
    )
    from src.company_roster import fetch_ticker_cik_map, resolve_target_ciks
    ticker_map = fetch_ticker_cik_map(sec_client, sec_settings.company_tickers_url)
    ciks, _ = resolve_target_ciks(target_tickers, ticker_map)
    cik_map = {t.upper(): c for t, c in zip(target_tickers, ciks)}

    frames: list[pd.DataFrame] = []
    records_collected = 0
    for blob in _iter_price_blobs(settings):
        if not blob.name.endswith(".jsonl") and not blob.name.endswith(".ndjson"):
            continue
        text = blob.download_as_text(encoding="utf-8")
        records = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if sample is not None and records_collected >= sample:
                break
            try:
                rec = _parse_price_line(line)
            except Exception:
                continue
            # Skip records with null timestamp or null current price
            if rec.get("timestamp") is None or rec.get("current") is None:
                continue
            rec["target_ticker"] = (rec.get("symbol") or "").upper()
            rec["target_cik"] = cik_map.get(rec["target_ticker"])
            rec["content_body"] = ""
            timestamp = rec.get("timestamp")
            if pd.notna(timestamp):
                rec["normalized_calendar_date"] = pd.to_datetime(timestamp).date().isoformat()
            else:
                rec["normalized_calendar_date"] = None
            rec["element_type"] = "quantitative"
            records.append(rec)
            records_collected += 1
        if records:
            frames.append(pd.DataFrame(records))
        if sample is not None and records_collected >= sample:
            break

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df[df["target_cik"].notna()].copy()
    logger.info("Loaded %d price rows after Fortune 500 filter", len(df))
    return df


def save_price_staging(df: pd.DataFrame, settings: LakehouseSettings) -> str:
    """Write price staging DataFrame to GCS Parquet."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = f"{settings.gcs_staging_prefix}/staging_finnhub.parquet"
    df = _coerce_schema(df)
    table = pa.Table.from_pandas(df, preserve_index=False)
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    blob = bucket.blob(path)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
    logger.info("Saved %d price rows to gs://%s/%s", len(df), settings.gcs_bucket, path)
    return path
