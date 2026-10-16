"""Admin-only endpoints for monitoring SEC data migration health."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import require_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/db-access-counters")
def get_db_access_counters(
    permission: str = require_permission("admin"),
) -> dict:
    """Return current DB access counter values.

    These counters track how many times deprecated PostgreSQL SEC functions
    were called since process start. After migration, all values should be 0.
    """
    from app.services.db_access_counter import get_counters

    counters = get_counters()
    has_hits = any(v > 0 for v in counters.values())

    return {
        "counters": counters,
        "total_hits": sum(counters.values()),
        "db_access_detected": has_hits,
        "all_clear": not has_hits,
    }


@router.post("/db-access-counters/reset")
def reset_db_access_counters(
    permission: str = require_permission("admin"),
) -> dict:
    """Reset all DB access counters to zero."""
    from app.services.db_access_counter import reset_counters

    reset_counters()
    return {"status": "reset", "counters": {}}


@router.get("/migration-status")
def get_migration_status(
    permission: str = require_permission("admin"),
) -> dict:
    """Return SEC data migration status summary."""
    from app.services.db_access_counter import get_counters
    from app.services.vectorized_gcs import count_vectorized_content

    counters = get_counters()
    has_db_hits = any(v > 0 for v in counters.values())

    try:
        gcs_count = count_vectorized_content()
    except Exception:
        gcs_count = -1

    return {
        "migration_complete": not has_db_hits,
        "db_access_detected": has_db_hits,
        "counters": counters,
        "vectorized_content_elements_in_gcs": gcs_count,
        "sec_endpoints_using_gcs": [
            "tickers.filings",
            "tickers.timeline (sec source)",
            "tickers.fiscal_year_end",
            "tickers.filing_content",
            "filings.elements",
            "search (sec source)",
            "dashboard.stats (articles_count)",
        ],
        "sec_endpoints_still_on_postgres": [
            k for k, v in counters.items() if v > 0
        ],
    }
