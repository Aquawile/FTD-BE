"""Service layer for vectorized SEC data.

Vectorized SEC filings live in GCS (``ftd-vectorized-data``) and are mirrored
chunk-for-chunk into PostgreSQL ``sec_vectorized_chunks`` by the sync cron
(scripts/sync_all_recent.sh -> sync_vectorized_to_postgres.py).

Every function reads only what its request needs, at request time:
  * filing lists, timeline events, filing elements, keyword search and
    ticker -> CIK lookups query ``sec_vectorized_chunks`` (indexed, scoped to
    one ticker / accession / keyword, most recent first);
  * raw filing HTML is read from ``raw-data-strg`` under one accession prefix.

Nothing is precomputed or cached, and no request lists or downloads the whole
bucket. Responses keep the relational shapes in app.models.
"""
from __future__ import annotations

import logging
import re
from datetime import date

from google.cloud import storage

from app.db import query_dict
from app.models import FiscalYearEnd, FilingElement, FilingSummary, SearchResult, TimelineEvent

logger = logging.getLogger(__name__)

_RAW_BUCKET = "raw-data-strg"
_SEC_PREFIX = "SEC/%"  # sec_vectorized_chunks.source_object = SEC/{form}/{CIK}/{accession}/{file}
_FILE_TICKER_RE = re.compile(r"^([a-z][a-z0-9_]*)-\d{8}\.(?:json|html?)$", re.IGNORECASE)


def _get_client() -> storage.Client:
    """Return a GCS storage client."""
    return storage.Client()


def _cik_prefixes(cik: str) -> tuple[str, str]:
    """LIKE patterns for one company's 8-K and 10-K files in the mirror."""
    cik_clean = cik.replace("-", "").zfill(10)
    return f"SEC/8-K/{cik_clean}/%", f"SEC/10-K/{cik_clean}/%"


def _form_from_path(source_object: str) -> str:
    return "8-K" if source_object.startswith("SEC/8-K/") else "10-K"


def _ticker_from_path(source_object: str) -> str | None:
    """Ticker from an inline-XBRL style filename (``nvda-20260125.htm``)."""
    match = _FILE_TICKER_RE.match(source_object.rsplit("/", 1)[-1])
    return match.group(1).upper() if match else None


def _resolve_ticker_to_cik(ticker: str) -> str | None:
    """Resolve ticker -> CIK from the vectorized filings' own paths.

    A filing stored as ``SEC/{form}/{CIK}/{accession}/{ticker}-{YYYYMMDD}.htm``
    ties the ticker to its CIK. One indexed-table query on first chunks only;
    the relational staging tables are not used because their target_cik is
    misaligned (see CLAUDE.md known issue #9).
    """
    rows = query_dict(
        r"""
        SELECT split_part(source_object, '/', 3) AS cik
        FROM sec_vectorized_chunks
        WHERE source_object LIKE %s
          AND chunk_index = 0
          AND lower(substring(source_object from '/([A-Za-z][A-Za-z0-9_]*)-[0-9]{8}\.html?$')) = %s
        LIMIT 1
        """,
        (_SEC_PREFIX, ticker.lower()),
    )
    return rows[0]["cik"] if rows else None


def _construct_edgar_url(cik: str, accession_number: str) -> str:
    """Construct SEC.gov EDGAR URL from CIK and accession number."""
    cik_clean = cik.replace("-", "")
    acc_clean = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getfile&CIK={cik_clean}&acckey={acc_clean}"
    )


def list_filings_for_ticker(ticker: str) -> list[FilingSummary]:
    """List a ticker's vectorized SEC filings, most recent first."""
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        logger.info("ticker_cik_not_found: ticker=%s", ticker)
        return []

    rows = query_dict(
        """
        SELECT source_object,
               MAX(accession_number) AS accession_number,
               MAX(form_type) AS form_type,
               MAX(filing_date) AS filing_date,
               COUNT(*) AS chunk_count
        FROM sec_vectorized_chunks
        WHERE source_object LIKE %s OR source_object LIKE %s
        GROUP BY source_object
        ORDER BY MAX(filing_date) DESC NULLS LAST, source_object
        """,
        _cik_prefixes(cik),
    )
    return [
        FilingSummary(
            target_ticker=ticker.upper(),
            target_cik=cik,
            form_type=r["form_type"] or "UNKNOWN",
            accession_number=r["accession_number"] or "",
            filing_date=r["filing_date"],
            element_count=r["chunk_count"],
            url=_construct_edgar_url(cik, r["accession_number"] or ""),
        )
        for r in rows
    ]


def get_filing_elements_by_accession(accession_number: str) -> list[FilingElement]:
    """Return one filing's text chunks (indexed lookup on accession_number)."""
    normalized = accession_number.upper().strip()
    digits = normalized.replace("-", "")
    dashed = f"{digits[:10]}-{digits[10:12]}-{digits[12:]}" if len(digits) == 18 else normalized

    rows = query_dict(
        """
        SELECT accession_number, filing_date, chunk_index, text_preview
        FROM sec_vectorized_chunks
        WHERE accession_number IN (%s, %s)
        ORDER BY chunk_index
        """,
        (dashed, normalized),
    )
    return [
        FilingElement(
            element_id=f"{r['accession_number']}-chunk-{r['chunk_index']}",
            accession_number=r["accession_number"],
            item_number="N/A",
            content_type="text/html",
            element_type="narrative",
            content_body=r["text_preview"] or "",
            raw_text_string=r["text_preview"] or "",
            period_of_report=None,
            filing_date=r["filing_date"],
            date_precision=None,
        )
        for r in rows
    ]


def search_vectorized_content(keyword: str, limit: int = 20) -> list[SearchResult]:
    """Keyword search over vectorized SEC chunks, most recent filings first."""
    pattern = "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = query_dict(
        r"""
        SELECT source_object, cik, accession_number, filing_date, chunk_index,
               LEFT(text_preview, 200) AS preview
        FROM sec_vectorized_chunks
        WHERE source_object LIKE %s AND text_preview ILIKE %s ESCAPE '\'
        ORDER BY filing_date DESC NULLS LAST, source_object, chunk_index
        LIMIT %s
        """,
        (_SEC_PREFIX, pattern, limit),
    )
    return [
        SearchResult(
            target_ticker=_ticker_from_path(r["source_object"]) or (r["cik"] or ""),
            normalized_calendar_date=r["filing_date"],
            source="sec",
            content_preview=r["preview"] or "",
            element_id=f"{r['accession_number'] or ''}-chunk-{r['chunk_index']}",
        )
        for r in rows
    ]


def count_vectorized_content() -> int:
    """Count vectorized SEC text chunks (one COUNT on the Postgres mirror)."""
    rows = query_dict(
        "SELECT COUNT(*) AS count FROM sec_vectorized_chunks WHERE source_object LIKE %s",
        (_SEC_PREFIX,),
    )
    return rows[0]["count"] if rows else 0


def get_filing_content_from_gcs(
    ticker: str,
    accession_no_dashes: str,
    cik_padded: str,
) -> tuple[bytes, str, bool]:
    """Fetch SEC filing HTML content directly from raw-data-strg GCS bucket.

    Returns (content_bytes, content_type, found_in_gcs).
    If not found in GCS, returns (b'', '', False) — caller should fallback to SEC.gov.

    Path format in raw-data-strg:
      SEC/{form_type}/{CIK_padded}/{accession_no_dashes}/{filename}.htm

    Since we don't know the exact filename, we list objects under the
    accession directory and find the .htm/.html file.
    """
    client = _get_client()
    bucket = client.bucket(_RAW_BUCKET)

    for form_type, prefix_pattern in [("8-K", "SEC/8-K/"), ("10-K", "SEC/10-K/")]:
        prefix = f"{prefix_pattern}{cik_padded}/{accession_no_dashes}/"
        blobs = list(bucket.list_blobs(prefix=prefix, max_results=10))
        for blob in blobs:
            if blob.name.endswith(".htm") or blob.name.endswith(".html"):
                content = blob.download_as_bytes()
                content_type = blob.content_type or "text/html"
                return content, content_type, True

    return b"", "", False


def get_timeline_from_gcs(
    ticker: str,
    start: date,
    end: date,
    limit: int = 100,
    offset: int = 0,
) -> list[TimelineEvent]:
    """SEC timeline events (one per filing) in a date range, most recent first."""
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        logger.info("ticker_cik_not_found: ticker=%s", ticker)
        return []

    prefix_8k, prefix_10k = _cik_prefixes(cik)
    rows = query_dict(
        """
        SELECT source_object, filing_date, LEFT(text_preview, 200) AS preview
        FROM sec_vectorized_chunks
        WHERE (source_object LIKE %s OR source_object LIKE %s)
          AND chunk_index = 0
          AND filing_date BETWEEN %s AND %s
        ORDER BY filing_date DESC, source_object
        LIMIT %s OFFSET %s
        """,
        (prefix_8k, prefix_10k, start, end, limit, offset),
    )
    return [
        TimelineEvent(
            normalized_calendar_date=r["filing_date"],
            source="sec",
            element_type="narrative",
            content_body=r["preview"] or "",
            current=None,
            change=None,
            form_type=_form_from_path(r["source_object"]),
            item_number="N/A",
            date_precision=None,
        )
        for r in rows
    ]


def get_fiscal_year_end_from_gcs(ticker: str) -> FiscalYearEnd | None:
    """Get fiscal year end from the fiscal_parameters table.

    Resolution flow:
      1. Resolve ticker → CIK (via _resolve_ticker_to_cik, one query on the
         vectorized mirror)
      2. Query fiscal_parameters by CIK
      3. Construct FiscalYearEnd response

    Note: the old deprecated function ``crud.get_ticker_fiscal_year_end``
    joined ``staging_sec`` on CIK — the new implementation resolves CIK
    independently and queries ``fiscal_parameters`` directly.
    """
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        logger.info("ticker_cik_not_found: ticker=%s", ticker)
        return None

    cik_clean = cik.replace("-", "").zfill(10)
    rows = query_dict(
        """
        SELECT
            %s AS target_ticker,
            %s AS target_cik,
            fiscal_year_end_date,
            source_accession
        FROM fiscal_parameters
        WHERE target_cik = %s
        LIMIT 1
        """,
        (ticker.upper(), cik, cik_clean),
    )
    if not rows:
        return None
    return FiscalYearEnd(**rows[0])
