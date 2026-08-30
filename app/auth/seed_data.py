from __future__ import annotations

from app.auth.permissions import ALL_PERMISSIONS
from app.db import query_dict


PERMISSION_DESCRIPTIONS = {
    "tickers.search": "Search available tickers",
    "tickers.prices": "View ticker price history",
    "tickers.news": "View ticker news and articles",
    "tickers.filings": "View SEC filings for a ticker",
    "tickers.timeline": "View ticker timeline events",
    "tickers.fiscal_year_end": "View fiscal year-end dates for tickers",
    "filings.read": "Read filing elements and content",
    "search.read": "Search content across all sources",
    "dashboard.read": "View dashboard stats and metrics",
}


def seed_permissions() -> None:
    existing = {row["name"] for row in query_dict("SELECT name FROM permissions")}
    inserted = 0
    skipped = 0
    for permission in sorted(ALL_PERMISSIONS):
        if permission in existing:
            skipped += 1
            continue
        description = PERMISSION_DESCRIPTIONS.get(permission, "")
        query_dict(
            "INSERT INTO permissions (name, description) VALUES (%s, %s)",
            (permission, description),
        )
        inserted += 1
    print(f"seed_permissions: {inserted} inserted, {skipped} already present, {len(ALL_PERMISSIONS)} total")


if __name__ == "__main__":
    seed_permissions()