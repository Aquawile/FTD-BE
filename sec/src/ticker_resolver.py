"""Backward-compatible shim — use company_roster and fortune500 instead."""

from src.company_roster import fetch_ticker_cik_map, resolve_target_ciks  # noqa: F401
