"""Normalize GNews sentiment JSON payloads into clean text staging rows."""

from __future__ import annotations

import json
import logging
import re
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


def _iter_gnews_blobs(settings: LakehouseSettings) -> Iterator[storage.Blob]:
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.raw_data_gcs_bucket)
    prefix = "gnews/"
    yield from bucket.list_blobs(prefix=prefix)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value))
    text = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return text.strip()


def _extract_query_tickers(query: str) -> list[str]:
    matches = re.findall(r"\$([A-Z]{1,5})", query)
    return [m for m in matches]


def load_gnews_frames(settings: LakehouseSettings, sample: int | None = None, since: str | None = None) -> pd.DataFrame:
    """Load GNews batch JSONs into a clean DataFrame with explicit schema."""
    sec_settings = settings.sec_settings
    storage = GcsStorage(sec_settings)
    error_logger = ErrorLogger(settings.project_root / "error_log_gnews.txt")
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
    allowed = set(cik_map.keys())

    since_dt = pd.Timestamp(since) if since else None
    frames: list[pd.DataFrame] = []
    rows_collected = 0
    for blob in _iter_gnews_blobs(settings):
        if not blob.name.endswith(".json"):
            continue
        if since_dt is not None and blob.time_created < since_dt:
            continue
        try:
            raw = blob.download_as_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", blob.name, exc)
            continue

        articles = payload.get("data", {}).get("articles", [])
        query = payload.get("query", "")
        tickers = _extract_query_tickers(query)
        if not tickers:
            continue

        rows = []
        for article in articles:
            if sample is not None and rows_collected >= sample:
                break
            title = _normalize_text(article.get("title"))
            description = _normalize_text(article.get("description"))
            content = _normalize_text(article.get("content"))

            body_parts = [p for p in (title, description, content) if p]
            content_body = ". ".join(body_parts)
            if len(content_body) < 50:
                continue

            published_at = article.get("publishedAt")
            ingest_date = (
                pd.to_datetime(published_at).date().isoformat() if published_at else None
            )

            for ticker in tickers:
                if sample is not None and rows_collected >= sample:
                    break
                if ticker not in allowed:
                    continue
                rows.append(
                    {
                        "target_ticker": ticker,
                        "target_cik": cik_map.get(ticker),
                        "element_type": "narrative",
                        "content_body": content_body,
                        "normalized_calendar_date": ingest_date,
                    }
                )
                rows_collected += 1
        if rows:
            frames.append(pd.DataFrame(rows))
        if sample is not None and rows_collected >= sample:
            break

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    logger.info("Loaded %d GNews article rows", len(df))
    return df


def save_gnews_staging(df: pd.DataFrame, settings: LakehouseSettings) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = f"{settings.gcs_staging_prefix}/staging_gnews.parquet"
    df = _coerce_schema(df)
    table = pa.Table.from_pandas(df, preserve_index=False)
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(path)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
    logger.info("Saved %d GNews rows to gs://%s/%s", len(df), settings.gcs_bucket, path)
    return path
