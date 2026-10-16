"""Dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def route_dashboard_stats() -> DashboardStats:
    from app.services.vectorized_gcs import count_vectorized_content
    from app.db import query_dict

    sec_count = count_vectorized_content()

    try:
        archive_rows = query_dict("SELECT COUNT(*) AS count FROM staging_sec_archive")
        articles_count = archive_rows[0]["count"] if archive_rows else 0
    except Exception:
        articles_count = sec_count

    tickers_rows = query_dict(
        "SELECT COUNT(DISTINCT symbol) AS count FROM tickers"
    )
    tickers_count = tickers_rows[0]["count"] if tickers_rows else 0

    alerts_rows = query_dict("SELECT COUNT(*) AS count FROM alerts")
    alerts_count = alerts_rows[0]["count"] if alerts_rows else 0

    return DashboardStats(
        articles_count=articles_count,
        tickers_count=tickers_count,
        alerts_count=alerts_count,
        evidence_score=None,
        vectorized_sec_count=sec_count,
    )
