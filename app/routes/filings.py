"""Filing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.crud import get_filing_elements
from app.models import FilingElement

router = APIRouter(prefix="/filings", tags=["filings"])


@router.get("/{accession_number}/elements", response_model=list[FilingElement])
def route_get_elements(
    accession_number: str,
    item_number: Annotated[str | None, Query(description="Item number filter")] = None,
    element_type: Annotated[str | None, Query(description="Element type filter (narrative or quantitative)")] = None,
) -> list[FilingElement]:
    return get_filing_elements(accession_number, item_number, element_type)
