"""Search endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.crud import search_content
from app.models import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


class SearchResponse(BaseModel):
    target_ticker: str
    normalized_calendar_date: date | None = None
    source: str = "sec"
    content_preview: str = ""
    element_id: str | None = None


@router.get("", response_model=list[SearchResponse])
def route_search(
    q: str = Query(..., min_length=1, description="Keyword to search across content"),
    source: Annotated[str | None, Query(description="Filter by source (finnhub, gnews, sec)")] = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[SearchResponse]:
    results = search_content(q, source, limit)
    return [SearchResponse(**r.model_dump()) for r in results]
