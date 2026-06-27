"""SEC company_tickers.json — live ticker-to-CIK lookup (not the target roster)."""

from __future__ import annotations

import json
import logging

from src.sec_client import SecClient

logger = logging.getLogger(__name__)

DEFAULT_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def fetch_ticker_cik_map(sec_client: SecClient, url: str) -> dict[str, str]:
    response = sec_client.fetch_url(url, cik="GLOBAL")
    if response is None:
        raise RuntimeError(f"Failed to fetch SEC ticker map from {url}")

    payload = json.loads(response.content)
    mapping: dict[str, str] = {}
    for entry in payload.values():
        ticker = str(entry["ticker"]).upper().replace(".", "-")
        cik = str(entry["cik_str"]).zfill(10)
        mapping[ticker] = cik

    logger.info("Loaded %s SEC ticker→CIK mappings", len(mapping))
    return mapping


def resolve_target_ciks(
    tickers: list[str],
    ticker_to_cik: dict[str, str],
) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()

    for ticker in tickers:
        cik = ticker_to_cik.get(ticker)
        if not cik:
            missing.append(ticker)
            continue
        if cik not in seen:
            resolved.append(cik)
            seen.add(cik)

    return resolved, missing
