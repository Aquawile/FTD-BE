"""Build GNews search queries from tickers and company names.

Each ticker is searched by its full company name and its ticker symbol:
    "NVIDIA" OR "NVDA" OR "Apple" OR "AAPL" ...
(a ticker without a known name is searched by its symbol alone). Terms are
spread over the daily request budget (GNews returns at most 10 articles per
query, so more, smaller queries return more articles), each query within
GNews's length limit. If the budget can't hold every ticker that way, terms
are packed tighter, and as a last resort the longest names are dropped (those
tickers fall back to ticker-only).

Pure functions, no I/O, so they can be unit tested without Flask or GCS.
"""
from __future__ import annotations

import math

MAX_QUERY_LENGTH = 200   # GNews limit for the q parameter
MAX_REQUESTS_PER_RUN = 100   # GNews free plan: 100 requests per day


def ticker_terms(ticker: str, names: dict[str, str]) -> list[str]:
    name = (names.get(ticker) or "").replace('"', "").strip()
    terms = [f'"{name}"'] if name and name.upper() != ticker.upper() else []
    terms.append(f'"{ticker}"')
    return terms


def _pack(tickers: list[str], names: dict[str, str], max_query_length: int,
          max_tickers_per_query: int | None = None) -> list[dict]:
    batches: list[dict] = []
    current_tickers: list[str] = []
    current_terms: list[str] = []
    for ticker in tickers:
        terms = ticker_terms(ticker, names)
        if len(" OR ".join(terms)) > max_query_length:  # name too long on its own: ticker only
            terms = [f'"{ticker}"']
        full = max_tickers_per_query is not None and len(current_tickers) >= max_tickers_per_query
        if current_tickers and (full or len(" OR ".join(current_terms + terms)) > max_query_length):
            batches.append({"tickers": current_tickers, "query": " OR ".join(current_terms)})
            current_tickers, current_terms = [], []
        current_tickers.append(ticker)
        current_terms.extend(terms)
    if current_tickers:
        batches.append({"tickers": current_tickers, "query": " OR ".join(current_terms)})
    return batches


def build_batches(
    tickers: list[str],
    names: dict[str, str],
    max_query_length: int = MAX_QUERY_LENGTH,
    max_requests: int = MAX_REQUESTS_PER_RUN,
) -> tuple[list[dict], list[str]]:
    """Return (batches, tickers whose name was dropped to fit the request budget)."""
    names = dict(names)
    dropped: list[str] = []
    spread = math.ceil(len(tickers) / max_requests) if tickers else None
    batches = _pack(tickers, names, max_query_length, spread)
    if len(batches) <= max_requests:
        return batches, dropped
    batches = _pack(tickers, names, max_query_length)
    by_length = sorted((t for t in tickers if t in names), key=lambda t: -len(names[t]))
    while len(batches) > max_requests and by_length:
        ticker = by_length.pop(0)
        names.pop(ticker)
        dropped.append(ticker)
        batches = _pack(tickers, names, max_query_length)
    if len(batches) > max_requests:
        raise ValueError(f"{len(tickers)} tickers need {len(batches)} queries even without names (budget {max_requests})")
    return batches, dropped
