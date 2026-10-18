"""Pydantic response models for the data-access layer."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TickerResult(BaseModel):
    ticker: str
    name: Optional[str] = None
    cik: str
    sector: Optional[str] = None
    news_snippet: Optional[str] = None


class PriceRow(BaseModel):
    normalized_calendar_date: Optional[date] = None
    current: Optional[Decimal] = None
    change: Optional[Decimal] = None
    percent_change: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None


class NewsRow(BaseModel):
    target_ticker: str
    normalized_calendar_date: Optional[date] = None
    ingest_date: Optional[date] = None
    content_body: str
    source: Optional[str] = None
    url: Optional[str] = None


class FilingSummary(BaseModel):
    target_ticker: str
    target_cik: str
    form_type: str
    accession_number: str
    filing_date: Optional[date] = None
    element_count: int = 0
    url: Optional[str] = None


class FilingElement(BaseModel):
    element_id: Optional[str] = None
    accession_number: str
    item_number: str
    content_type: str
    element_type: Literal["quantitative", "narrative", ""] = ""
    content_body: str
    raw_text_string: Optional[str] = None
    period_of_report: Optional[date] = None
    filing_date: Optional[date] = None
    date_precision: Optional[str] = None


class FiscalYearEnd(BaseModel):
    target_ticker: str
    target_cik: str
    fiscal_year_end_date: Optional[date] = None
    source_accession: Optional[str] = None


class TimelineEvent(BaseModel):
    normalized_calendar_date: Optional[date] = None
    source: Literal["finnhub", "gnews", "sec"] = "sec"
    element_type: Literal["quantitative", "narrative", ""] = ""
    content_body: str = ""
    current: Optional[Decimal] = None
    change: Optional[Decimal] = None
    form_type: Optional[str] = None
    item_number: Optional[str] = None
    date_precision: Optional[str] = None


class SearchResult(BaseModel):
    target_ticker: str
    normalized_calendar_date: Optional[date] = None
    source: Literal["finnhub", "gnews", "sec"] = "sec"
    content_preview: str = ""
    element_id: Optional[str] = None


class DashboardStats(BaseModel):
    articles_count: int = 0          # news_articles_count + sec_filings_count
    news_articles_count: int = 0     # distinct news articles (staging_gnews, by URL)
    sec_filings_count: int = 0       # distinct SEC filings (archive + vectorized mirror)
    tickers_count: int = 0
    alerts_count: int = 0
    evidence_score: Optional[float] = None
    vectorized_sec_count: int = 0


class TrackedTicker(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    evidence_score: Optional[float] = None
    hype_score: Optional[float] = None
    change_percent: Optional[float] = None
    price_as_of: Optional[str] = None


class PriceTimelinePoint(BaseModel):
    date: date
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    percent_change: Optional[float] = None
    has_data: bool = False


class PriceTimeline(BaseModel):
    ticker: str
    window_days: int
    window_start: Optional[date] = None
    window_end: Optional[date] = None
    first_data_date: Optional[date] = None
    last_data_date: Optional[date] = None
    trading_days: int = 0
    days_covered: int = 0
    fill_ratio: float = 0.0
    points: list[PriceTimelinePoint] = Field(default_factory=list)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    tickers: list[str] = []
    alerts: int = 0
    created_at: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    ticker: Optional[str] = None
    type: str
    message: str
    read: bool = False
    severity: str = "medium"
    time: Optional[str] = None
    subscription_id: Optional[int] = None


class AlertSummary(BaseModel):
    unread_count: int = 0
    newest_unread: Optional[AlertResponse] = None


# What a subscription watches. Price types need a threshold; news/filing don't.
AlertType = Literal["price_above", "price_below", "news", "filing"]
PRICE_ALERT_TYPES = ("price_above", "price_below")


class AlertSubscriptionCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    alert_type: AlertType
    threshold: Optional[float] = Field(default=None, gt=0)


class AlertSubscriptionUpdate(BaseModel):
    active: Optional[bool] = None
    threshold: Optional[float] = Field(default=None, gt=0)


class AlertSubscriptionResponse(BaseModel):
    id: int
    ticker: str
    alert_type: str
    threshold: Optional[float] = None
    active: bool
    created_at: Optional[str] = None
    last_observed_label: Optional[str] = None
    last_evaluated_at: Optional[str] = None
    last_alerted_at: Optional[str] = None
