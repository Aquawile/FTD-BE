"""Dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def route_dashboard_stats() -> DashboardStats:
    from app.crud import count_articles
    from app.db import query_dict
    from app.services.vectorized_gcs import count_vectorized_content

    sec_count = count_vectorized_content()
    news_count, filings_count, sec_elements = count_articles()

    tickers_rows = query_dict(
        "SELECT COUNT(DISTINCT symbol) AS count FROM tickers"
    )
    tickers_count = tickers_rows[0]["count"] if tickers_rows else 0

    return DashboardStats(
        articles_count=sec_elements + news_count,
        sec_elements_count=sec_elements,
        news_articles_count=news_count,
        sec_filings_count=filings_count,
        tickers_count=tickers_count,
        vectorized_sec_count=sec_count,
    )
