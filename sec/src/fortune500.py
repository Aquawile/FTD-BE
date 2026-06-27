"""Fetch the target ~500 company ticker list and cross-reference with SEC CIKs."""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import TYPE_CHECKING

from src.sec_client import SecClient

if TYPE_CHECKING:
    from src.gcs_storage import GcsStorage

logger = logging.getLogger(__name__)

DEFAULT_FORTUNE_500_FALLBACK_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "master/data/constituents.csv"
)


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper().lstrip("$").replace(".", "-")


def _parse_ticker_payload(payload: object) -> list[str]:
    if isinstance(payload, list):
        if not payload:
            return []
        if isinstance(payload[0], str):
            return [normalize_ticker(t) for t in payload]
        if isinstance(payload[0], dict):
            tickers: list[str] = []
            for entry in payload:
                raw = entry.get("ticker") or entry.get("symbol") or entry.get("Symbol")
                if raw:
                    tickers.append(normalize_ticker(str(raw)))
            return tickers

    if isinstance(payload, dict):
        for key in ("tickers", "symbols", "companies"):
            if key in payload:
                return _parse_ticker_payload(payload[key])

    raise ValueError("Unsupported Fortune 500 JSON shape; expected a ticker array")


def _parse_csv_tickers(content: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return []
    symbol_key = next(
        (name for name in reader.fieldnames if name.lower() in {"symbol", "ticker"}),
        None,
    )
    if symbol_key is None:
        raise ValueError("CSV must include a Symbol or ticker column")
    return [normalize_ticker(row[symbol_key]) for row in reader if row.get(symbol_key)]


def _parse_ticker_document(content: bytes, *, source: str) -> list[str]:
    text = content.decode("utf-8")
    if source.endswith(".csv") or "symbol" in text.split("\n", 1)[0].lower():
        return _parse_csv_tickers(text)
    return _parse_ticker_payload(json.loads(text))


def _dedupe_limit(tickers: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for ticker in tickers:
        if ticker in seen:
            continue
        seen.add(ticker)
        result.append(ticker)
        if len(result) >= limit:
            break
    return result


def fetch_target_tickers_from_bytes(
    content: bytes,
    *,
    source: str,
    limit: int,
) -> list[str]:
    tickers = _dedupe_limit(_parse_ticker_document(content, source=source), limit)
    if not tickers:
        raise RuntimeError(f"No tickers parsed from {source}")
    logger.info("Loaded %s target tickers from %s", len(tickers), source)
    return tickers


def fetch_target_tickers_from_http(
    sec_client: SecClient,
    url: str,
    *,
    limit: int,
) -> list[str]:
    response = sec_client.fetch_url(url, cik="F500")
    if response is None:
        raise RuntimeError(f"Failed to fetch target ticker list from {url}")
    return fetch_target_tickers_from_bytes(
        response.content,
        source=url,
        limit=limit,
    )


def fetch_target_tickers(
    sec_client: SecClient,
    storage: GcsStorage,
    *,
    gcs_path: str,
    fallback_url: str,
    limit: int,
) -> list[str]:
    """Load top-N tickers from GCS JSON/CSV, falling back to a public CSV source."""
    blob_path = gcs_path.strip()
    if blob_path.startswith("gs://"):
        blob_path = blob_path.split("/", 3)[-1]

    content = storage.download_config_blob(blob_path)
    if content is not None:
        try:
            return fetch_target_tickers_from_bytes(
                content,
                source=blob_path,
                limit=limit,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Invalid roster in %s (%s); using fallback", blob_path, exc)

    logger.info("Roster file missing or invalid; fetching fallback from %s", fallback_url)
    tickers = fetch_target_tickers_from_http(sec_client, fallback_url, limit=limit)
    storage.upload_config_blob(
        blob_path,
        _roster_document(tickers),
        content_type="application/json",
    )
    return tickers


def _roster_document(tickers: list[str]) -> bytes:
    payload = {
        "source": "pipeline-bootstrap",
        "tickers": tickers,
    }
    return json.dumps(payload, indent=2).encode("utf-8")
