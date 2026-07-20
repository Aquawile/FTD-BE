"""Pydantic response models for the data-access layer."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TickerResult(BaseModel):
    ticker: str
    cik: str


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


class FilingSummary(BaseModel):
    target_ticker: str
    target_cik: str
    form_type: str
    accession_number: str
    filing_date: Optional[date] = None
    element_count: int = 0


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
