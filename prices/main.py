#!/usr/bin/env python3
"""Finnhub current price ingestion to GCS — free tier, non-commercial."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any

from google.cloud import storage

logger = logging.getLogger(__name__)

GCS_BUCKET = os.environ.get("GCS_BUCKET", "raw-data-strg")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "prices")
TICKERS_GCS_PATH = os.environ.get("TICKERS_GCS_PATH", "SEC/config/fortune500.json")
FINNHUB_SECRET_NAME = os.environ.get("FINNHUB_SECRET_NAME", "finnhub-api-key")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "ftd2026")

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
REQUEST_DELAY_SECONDS = 1.0
MAX_CONSECUTIVE_FAILURES = 5


def _get_gcs_bucket() -> storage.Bucket:
    return storage.Client().bucket(GCS_BUCKET)


def load_tickers(bucket: storage.Bucket, blob_path: str) -> list[str]:
    blob = bucket.blob(blob_path)
    content = blob.download_as_text()
    payload = json.loads(content)
    if isinstance(payload, dict) and "tickers" in payload:
        tickers = payload["tickers"]
    elif isinstance(payload, list):
        tickers = payload
    else:
        raise ValueError(f"Unexpected ticker JSON shape: {type(payload)}")
    result, seen = [], set()
    for raw in tickers:
        ticker = str(raw).strip().upper().replace(".", "-")
        if ticker not in seen:
            seen.add(ticker)
            result.append(ticker)
    return result


def get_finnhub_api_key() -> str:
    from google.cloud import secretmanager_v1
    client = secretmanager_v1.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{FINNHUB_SECRET_NAME}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
    except Exception as exc:
        raise RuntimeError(
            f"Failed to access Finnhub API key from Secret Manager "
            f"(secret={FINNHUB_SECRET_NAME}, project={GCP_PROJECT}): {exc}"
        ) from exc
    key = response.payload.data.decode("UTF-8")
    if not key:
        raise RuntimeError(
            f"Finnhub API key is empty. Check secret '{FINNHUB_SECRET_NAME}' "
            f"in project '{GCP_PROJECT}'."
        )
    return key


def fetch_quote(api_key: str, symbol: str) -> dict[str, Any] | None:
    """Fetch current quote snapshot for a single ticker from Finnhub."""
    url = f"{FINNHUB_QUOTE_URL}?symbol={urllib.parse.quote(symbol)}&token={api_key}"
    req = urllib.request.Request(url, headers={"User-Agent": "FTD-Finnhub-Prices/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("c") is not None:
                return data
            logger.warning("Unexpected quote payload for %s: %s", symbol, data)
            return None
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            logger.warning("Rate limited on %s, backing off 2s...", symbol)
            time.sleep(2.0)
            return fetch_quote(api_key, symbol)
        logger.error("Finnhub HTTP error %d for %s: %s", exc.code, symbol, exc.reason)
        return None
    except Exception as exc:
        logger.warning("Fetch error for %s: %s", symbol, exc)
        return None


def serialize_quote(symbol: str, data: dict[str, Any]) -> str | None:
    """Convert Finnhub quote response to JSON record."""
    try:
        record = {
            "symbol": symbol,
            "timestamp": datetime.fromtimestamp(data.get("t", 0), tz=timezone.utc).isoformat(),
            "current": round(float(data.get("c", 0)), 4),
            "change": round(float(data.get("d", 0)), 4),
            "percent_change": round(float(data.get("dp", 0)), 4),
            "high": round(float(data.get("h", 0)), 4),
            "low": round(float(data.get("l", 0)), 4),
            "open": round(float(data.get("o", 0)), 4),
            "previous_close": round(float(data.get("pc", 0)), 4),
        }
        return json.dumps(record, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.warning("Serialize error for %s: %s", symbol, exc)
        return None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    bucket = _get_gcs_bucket()
    logger.info("Loading tickers from gs://%s/%s", GCS_BUCKET, TICKERS_GCS_PATH)
    tickers = load_tickers(bucket, TICKERS_GCS_PATH)
    logger.info("Loaded %d tickers", len(tickers))
    if not tickers:
        raise RuntimeError("No tickers loaded")

    try:
        api_key = get_finnhub_api_key()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    storage_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    gcs_path = f"{GCS_PREFIX}/{storage_date}/data.jsonl"
    blob = bucket.blob(gcs_path)
    if blob.exists():
        logger.info("Data for %s already exists at gs://%s/%s — skipping fetch", storage_date, GCS_BUCKET, gcs_path)
        logger.info("Pipeline complete (no-op)")
        return 0

    logger.info("Fetching Finnhub quotes for %d tickers (%s)", len(tickers), storage_date)

    all_records = []
    failed = []
    consecutive_failures = 0
    start_time = time.time()

    for idx, ticker in enumerate(tickers):
        data = fetch_quote(api_key, ticker)
        if data is None:
            failed.append(ticker)
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    "Aborting pipeline after %d consecutive failures. "
                    "Last failed ticker: %s. Check your Finnhub API key and Secret Manager config.",
                    consecutive_failures,
                    ticker,
                )
                return 1
        else:
            consecutive_failures = 0
            record = serialize_quote(ticker, data)
            if record:
                all_records.append(record)

        if (idx + 1) % 50 == 0:
            elapsed = time.time() - start_time
            logger.info("Progress: %d/%d tickers in %.1fs", idx + 1, len(tickers), elapsed)
        time.sleep(REQUEST_DELAY_SECONDS)

    total_time = time.time() - start_time
    logger.info(
        "Fetched %d records for %d tickers in %.1fs (failed: %d)",
        len(all_records),
        len(tickers),
        total_time,
        len(failed),
    )
    if failed:
        logger.warning("Failed tickers: %s", ", ".join(failed[:20]))

    if not all_records:
        logger.warning("No records fetched - writing empty file")

    content = "\n".join(all_records) + "\n" if all_records else ""
    record_count = len(all_records)

    blob.upload_from_string(content, content_type="application/x-ndjson")
    logger.info("Wrote %d records to gs://%s/%s", record_count, GCS_BUCKET, gcs_path)
    logger.info("Pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
