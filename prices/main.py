#!/usr/bin/env python3
"""Databento EOD price ingestion to GCS — free tier, historical slice only."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from google.cloud import storage

logger = logging.getLogger(__name__)

GCS_BUCKET = os.environ.get("GCS_BUCKET", "raw-data-strg")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "prices")
TICKERS_GCS_PATH = os.environ.get("TICKERS_GCS_PATH", "SEC/config/fortune500.json")
DATABENTO_SECRET_NAME = os.environ.get("DATABENTO_SECRET_NAME", "databento-api-key")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "ftd2026")

DATASET = "XNAS.ITCH"
SCHEMA = "ohlcv-1m"
LOOKBACK_DAYS = 4  # days back to ensure historical data before live cutoff
MAX_COST_USD = 0.05
MIN_BALANCE_USD = 1.00


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


def get_databento_api_key() -> str:
    from google.cloud import secretmanager_v1
    client = secretmanager_v1.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT}/secrets/{DATABENTO_SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def _init_databento_client(api_key: str) -> Any:
    import databento as db
    return db.Historical(key=api_key)


def check_cost_estimate(client: Any, tickers: list[str], start_date: str, end_date: str) -> float:
    try:
        # Use a small sample for cost estimate to avoid large requests
        sample = tickers[:10] if len(tickers) > 10 else tickers
        estimate = client.metadata.get_cost(
            dataset=DATASET,
            symbols=sample,
            schema=SCHEMA,
            start=start_date,
            end=end_date,
        )
        if isinstance(estimate, dict):
            return float(estimate.get("total_usd", estimate.get("total", 0)))
        if hasattr(estimate, "total_usd"):
            return float(estimate.total_usd)
        return float(estimate)
    except Exception as exc:
        logger.warning("Could not retrieve cost estimate: %s", exc)
        return 0.0


def check_credit_balance(client: Any) -> float | None:
    try:
        if hasattr(client, "metadata") and hasattr(client.metadata, "get_balance"):
            return float(client.metadata.get_balance())
        if hasattr(client, "get_balance"):
            return float(client.get_balance())
        if hasattr(client, "account"):
            info = client.account()
            if isinstance(info, dict):
                return float(info.get("balance", info.get("credits_remaining", 0)))
        return None
    except Exception as exc:
        logger.warning("Could not check credit balance: %s", exc)
        return None


def fetch_prices(client: Any, tickers: list[str], start_date: str, end_date: str) -> Any:
    return client.timeseries.get_range(
        dataset=DATASET,
        symbols=tickers,
        schema=SCHEMA,
        start=start_date,
        end=end_date,
    )


def serialize_records(data: Any) -> str:
    df = data.to_df() if hasattr(data, "to_df") else None
    if df is None or df.empty:
        return ""

    df = df.reset_index()
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            val = row[col]
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            elif hasattr(val, "item"):
                val = val.item()
            record[col] = val
        records.append(record)
    return "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in records) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    bucket = _get_gcs_bucket()
    logger.info("Loading tickers from gs://%s/%s", GCS_BUCKET, TICKERS_GCS_PATH)
    tickers = load_tickers(bucket, TICKERS_GCS_PATH)
    logger.info("Loaded %d tickers", len(tickers))
    if not tickers:
        raise RuntimeError("No tickers loaded")

    # Databento uses dot notation for class shares (BRK.B not BRK-B)
    databento_tickers = [t.replace("-", ".") for t in tickers]

    api_key = get_databento_api_key()
    client = _init_databento_client(api_key)

    # Historical slice: find the most recent completed trading day
    # and use its 15:59-16:00 window (the official EOD close bar)
    now_utc = datetime.now(timezone.utc)
    # Try yesterday first, then walk back if weekend/holiday
    candidate = now_utc - timedelta(days=LOOKBACK_DAYS)
    while candidate.weekday() >= 5:  # Saturday=5, Sunday=6
        candidate -= timedelta(days=1)

    start_date = candidate.strftime("%Y-%m-%dT15:59:00")
    end_date = candidate.strftime("%Y-%m-%dT16:00:00")
    storage_date = candidate.strftime("%Y-%m-%d")

    logger.info("Checking cost estimate...")
    estimated_cost = check_cost_estimate(client, databento_tickers, start_date, end_date)
    logger.info("Estimated cost: $%.4f", estimated_cost)
    if estimated_cost > MAX_COST_USD:
        raise RuntimeError(f"Pipeline Aborted: cost ${estimated_cost:.4f} > ${MAX_COST_USD}")

    logger.info("Checking credit balance...")
    balance = check_credit_balance(client)
    if balance is not None:
        logger.info("Current balance: $%.2f", balance)
        if balance <= MIN_BALANCE_USD:
            raise RuntimeError(f"Pipeline Aborted: balance ${balance:.2f} <= ${MIN_BALANCE_USD}")
    else:
        logger.warning("Could not retrieve balance — proceeding with caution")

    logger.info("Fetching %s data for %d tickers (%s -> %s)...", SCHEMA, len(databento_tickers), start_date, end_date)
    data = fetch_prices(client, databento_tickers, start_date, end_date)

    content = serialize_records(data)
    record_count = content.count("\n")
    logger.info("Fetched %d records", record_count)

    gcs_path = f"{GCS_PREFIX}/{storage_date}/data.jsonl"
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(content, content_type="application/x-ndjson")
    logger.info("Wrote %d records to gs://%s/%s", record_count, GCS_BUCKET, gcs_path)
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
