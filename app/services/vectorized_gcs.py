"""Service layer for reading vectorized SEC data from GCS.

All read operations target the `ftd-vectorized-data` bucket.
PostgreSQL is used ONLY for ticker-to-CIK resolution (user metadata).
No SEC filing content is read from PostgreSQL in this module.

Data flow:
  1. UI calls API endpoint (e.g., GET /api/tickers/AAPL/filings)
  2. Route delegates to function in this module
  3. Function resolves ticker → CIK via PostgreSQL tickers table (relational metadata)
  4. Function reads vectorized JSON from ftd-vectorized-data (GCS)
  5. Function constructs Pydantic model objects from JSON
  6. API returns response to frontend (no frontend changes needed)
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date, datetime
from typing import Iterator

from google.cloud import storage
from app.models import FiscalYearEnd, FilingElement, FilingSummary, SearchResult, TimelineEvent

logger = logging.getLogger(__name__)

_BUCKET = os.environ.get("VECTORIZED_OUTPUT_BUCKET", "ftd-vectorized-data")
_RAW_BUCKET = "raw-data-strg"
_SEC_FORMS = ("sec-8k", "sec-10k")
_MAX_TEXT_LENGTH = 100000


def _get_client() -> storage.Client:
    """Return a GCS storage client."""
    return storage.Client()


def _list_vectorized_blobs(prefix: str) -> Iterator[storage.Blob]:
    """Yield Storage Blob objects for all .json files under the given prefix."""
    client = _get_client()
    bucket = client.bucket(_BUCKET)
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if blob.name.endswith(".json"):
            yield blob


def _download_filing_json(blob: storage.Blob) -> dict:
    """Download and parse a vectorized filing JSON object."""
    data = blob.download_as_bytes()
    return json.loads(data.decode("utf-8"))


def _resolve_ticker_to_cik(ticker: str) -> str | None:
    """Resolve ticker symbol to CIK.

    Tries multiple sources in order:
      1. PostgreSQL ``tickers`` table (``cik`` column — may not exist in all schemas)
      2. PostgreSQL ``unified_staging`` table (``target_cik`` column)
      3. GCS blob name paths (parses ``{form}/{CIK}/{accession}/{ticker}-*.json``)

    Only steps 1–2 are PostgreSQL calls and are for relational user metadata,
    not SEC filing content. Step 3 reads from ``ftd-vectorized-data``.
    """
    from app.db import query_dict

    ticker_upper = ticker.upper()

    # Step 1: tickers table (if the cik column exists)
    try:
        rows = query_dict(
            "SELECT cik FROM tickers WHERE symbol = %s AND cik IS NOT NULL LIMIT 1",
            (ticker_upper,),
        )
        if rows:
            return rows[0]["cik"]
    except Exception:
        pass

    # Step 2: unified_staging fallback
    try:
        rows = query_dict(
            "SELECT DISTINCT target_cik FROM unified_staging WHERE target_ticker = %s LIMIT 1",
            (ticker_upper,),
        )
        if rows:
            return rows[0]["target_cik"]
    except Exception:
        pass

    # Step 3: parse GCS blob names (no content download needed)
    return _resolve_ticker_to_cik_from_blob_names(ticker_upper)


def _resolve_ticker_to_cik_from_blob_names(ticker: str) -> str | None:
    """Resolve ticker → CIK by parsing GCS blob name paths.

    Blob names follow the pattern:
        sec-{form}/{CIK}/{accession}/{ticker}-{date}.json

    Listing blob names is a metadata-only operation (no content download),
    so it is fast even with hundreds of files.
    """
    import re

    ticker_lower = ticker.lower()
    pattern = re.compile(r"^([a-z][a-z0-9_]*)-\d{8}\.json$", re.IGNORECASE)

    client = _get_client()
    bucket = client.bucket(_BUCKET)

    for form_dir in _SEC_FORMS:
        for blob in bucket.list_blobs(prefix=f"{form_dir}/"):
            if not blob.name.endswith(".json"):
                continue
            parts = blob.name.split("/")
            if len(parts) < 4:
                continue
            filename = parts[-1]
            match = pattern.match(filename)
            if match and match.group(1).lower() == ticker_lower:
                # CIK is the second path component (after form_dir)
                cik = parts[1]
                if cik:
                    return cik
    return None


def _parse_date(date_str: str | None) -> date | None:
    """Parse an ISO date string from sec_metadata into a date object."""
    if not date_str:
        return None
    if isinstance(date_str, date):
        return date_str
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        return None


def _construct_edgar_url(cik: str, accession_number: str) -> str:
    """Construct SEC.gov EDGAR URL from CIK and accession number."""
    cik_clean = cik.replace("-", "")
    acc_clean = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getfile&CIK={cik_clean}&acckey={acc_clean}"
    )


def list_filings_for_ticker(ticker: str) -> list[FilingSummary]:
    """List SEC filings for a ticker from vectorized GCS data.

    Flow:
      1. Resolve ticker → CIK (PostgreSQL tickers table — relational metadata)
      2. List JSON files in ftd-vectorized-data/sec-8k/{CIK}/ and sec-10k/{CIK}/
      3. Parse sec_metadata from each JSON file
      4. Construct FilingSummary objects

    Returns: list of FilingSummary sorted by filing_date DESC.
    """
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        logger.info("ticker_cik_not_found: ticker=%s", ticker)
        return []

    cik_clean = cik.replace("-", "").zfill(10)
    results: list[FilingSummary] = []

    for form_dir in _SEC_FORMS:
        prefix = f"{form_dir}/{cik_clean}/"
        for blob in _list_vectorized_blobs(prefix):
            try:
                parsed = _download_filing_json(blob)
            except Exception as e:
                logger.warning("vectorized_gcs_read_failed: blob=%s error=%s", blob.name, e)
                continue

            meta = parsed.get("sec_metadata", {})
            accession = meta.get("accession_number", "")
            filing_date = _parse_date(meta.get("filing_date"))
            form_type = meta.get("form", "UNKNOWN")
            chunk_count = len(parsed.get("chunks", []))

            results.append(FilingSummary(
                target_ticker=ticker.upper(),
                target_cik=cik,
                form_type=form_type,
                accession_number=accession,
                filing_date=filing_date,
                element_count=chunk_count,
                url=_construct_edgar_url(cik, accession),
            ))

    results.sort(key=lambda x: x.filing_date or date.min, reverse=True)
    return results


def get_filing_elements_by_accession(accession_number: str) -> list[FilingElement]:
    """Retrieve filing elements (chunks) from vectorized data.

    Extracts the CIK from the accession number (format: ``CIK-YY-NNNNNN``)
    and searches only within that CIK's directory in GCS, making this
    O(1) directory lookup instead of scanning all ~707 files.

    Falls back to a full scan if the CIK cannot be extracted.
    """
    normalized = accession_number.upper().strip()
    normalized_no_dashes = normalized.replace("-", "")

    # Extract CIK from accession number (format: CIK-YY-NNNNNN)
    cik = None
    parts = normalized.split("-")
    if len(parts) >= 3:
        cik = parts[0].zfill(10)

    # If CIK is known, search only within that directory (fast path)
    if cik:
        for form_dir in _SEC_FORMS:
            prefix = f"{form_dir}/{cik}/"
            for blob in _list_vectorized_blobs(prefix):
                try:
                    parsed = _download_filing_json(blob)
                except Exception:
                    continue

                meta = parsed.get("sec_metadata", {})
                meta_accession = meta.get("accession_number", "")
                if meta_accession and meta_accession.replace("-", "") == normalized_no_dashes:
                    return _extract_filing_elements(parsed, meta)

    # Slow path: scan all blobs (fallback when CIK can't be extracted)
    for form_dir in _SEC_FORMS:
        for blob in _list_vectorized_blobs(f"{form_dir}/"):
            try:
                parsed = _download_filing_json(blob)
            except Exception:
                continue

            meta = parsed.get("sec_metadata", {})
            meta_accession = meta.get("accession_number", "")
            if meta_accession and meta_accession.replace("-", "") == normalized_no_dashes:
                return _extract_filing_elements(parsed, meta)

    return []


def _extract_filing_elements(parsed: dict, meta: dict) -> list[FilingElement]:
    """Convert vectorized JSON chunks into FilingElement objects."""
    accession = meta.get("accession_number", "")
    filing_date = _parse_date(meta.get("filing_date"))

    elements: list[FilingElement] = []
    for i, chunk in enumerate(parsed.get("chunks", [])):
        elements.append(FilingElement(
            element_id=f"{accession}-chunk-{i}",
            accession_number=accession,
            item_number="N/A",
            content_type="text/html",
            element_type="narrative",
            content_body=chunk.get("text_preview", ""),
            raw_text_string=chunk.get("text_preview", ""),
            period_of_report=None,
            filing_date=filing_date,
            date_precision=None,
        ))

    return elements


def search_vectorized_content(keyword: str, limit: int = 20) -> list[SearchResult]:
    """Search across vectorized text chunks for a keyword.

    Performs keyword substring search across all chunks' text_preview fields
    in sec-8k/ and sec-10k/ directories. Uses concurrent downloads for
    performance (700+ files would take too long sequentially).

    Returns list of SearchResult objects.
    """
    import concurrent.futures

    results: list[SearchResult] = []
    kw_lower = keyword.lower()
    _search_lock = __import__("threading").Lock()

    # Collect all blob names first (metadata-only, fast)
    client = _get_client()
    bucket = client.bucket(_BUCKET)

    all_blobs: list[storage.Blob] = []
    for form_dir in _SEC_FORMS:
        for blob in bucket.list_blobs(prefix=f"{form_dir}/"):
            if blob.name.endswith(".json"):
                all_blobs.append(blob)

    def _process_blob(blob: storage.Blob, form_type_str: str) -> list[SearchResult]:
        """Download and search a single filing JSON. Returns matching results."""
        try:
            data = blob.download_as_bytes()
            parsed = json.loads(data.decode("utf-8"))
        except Exception:
            return []

        meta = parsed.get("sec_metadata", {})
        accession = meta.get("accession_number", "")
        cik = meta.get("cik", "")

        # Extract ticker from blob name (avoids expensive PG/GCS lookup per file)
        # Path: sec-{form}/{CIK}/{accession}/{ticker}-{date}.json
        ticker = _extract_ticker_from_blob_name(blob.name) or cik

        local: list[SearchResult] = []
        for chunk in parsed.get("chunks", []):
            preview = chunk.get("text_preview", "")
            if kw_lower in preview.lower():
                local.append(SearchResult(
                    target_ticker=ticker.upper(),
                    normalized_calendar_date=_parse_date(meta.get("filing_date")),
                    source="sec",
                    content_preview=preview[:200],
                    element_id=f"{accession}-chunk-{chunk.get('chunk_index')}",
                ))

        return local

    # Determine form_type for each blob
    blob_form_pairs = []
    for blob in all_blobs:
        form_type_str = "8-K" if blob.name.startswith("sec-8k/") else "10-K"
        blob_form_pairs.append((blob, form_type_str))

    # Process blobs concurrently (I/O bound, thread pool is appropriate)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_blob = {
            executor.submit(_process_blob, blob, ft): blob
            for blob, ft in blob_form_pairs
        }
        for future in concurrent.futures.as_completed(future_to_blob):
            if len(results) >= limit:
                break
            try:
                matches = future.result()
                with _search_lock:
                    results.extend(matches)
            except Exception:
                continue

    return results[:limit]


def _resolve_cik_to_ticker(cik: str) -> str | None:
    """Resolve CIK → ticker.

    Tries PostgreSQL first (tickers table if ``cik`` column exists, then
    unified_staging), then falls back to GCS blob name parsing.
    """
    from app.db import query_dict

    cik_clean = cik.replace("-", "").zfill(10)

    # Step 1: tickers table (if the cik column exists)
    try:
        rows = query_dict(
            "SELECT symbol FROM tickers WHERE cik = %s OR cik = %s LIMIT 1",
            (cik, cik_clean),
        )
        if rows:
            return rows[0]["symbol"]
    except Exception:
        pass

    # Step 2: unified_staging fallback
    try:
        rows = query_dict(
            "SELECT DISTINCT target_ticker FROM unified_staging WHERE target_cik = %s LIMIT 1",
            (cik,),
        )
        if rows:
            return rows[0]["target_ticker"]
    except Exception:
        pass

    # Step 3: parse GCS blob names (metadata-only, no content download)
    return _resolve_cik_to_ticker_from_blob_names(cik_clean)


def _extract_ticker_from_blob_name(blob_name: str) -> str | None:
    """Extract ticker symbol from a GCS blob name.

    Blob names follow the pattern:
        sec-{form}/{CIK}/{accession}/{ticker}-{date}.json

    Returns the ticker (uppercase) or None if the pattern doesn't match.
    """
    import re
    parts = blob_name.split("/")
    if len(parts) < 2:
        return None
    filename = parts[-1]
    match = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)-\d{8}\.json$", filename)
    if match:
        return match.group(1).upper()
    return None


def _resolve_cik_to_ticker_from_blob_names(cik: str) -> str | None:
    """Resolve CIK → ticker by parsing GCS blob name paths.

    Looks for blobs under ``sec-{form}/{CIK}/`` and extracts the ticker
    from the filename pattern ``{ticker}-{date}.json``.
    """
    import re

    pattern = re.compile(r"^([a-z][a-z0-9_]*)-\d{8}\.json$", re.IGNORECASE)

    client = _get_client()
    bucket = client.bucket(_BUCKET)

    for form_dir in _SEC_FORMS:
        prefix = f"{form_dir}/{cik}/"
        for blob in bucket.list_blobs(prefix=prefix, max_results=1):
            if blob.name.endswith(".json"):
                parts = blob.name.split("/")
                if len(parts) >= 4:
                    filename = parts[-1]
                    match = pattern.match(filename)
                    if match:
                        return match.group(1).upper()
    return None


# Chunk counts per vectorized file, keyed on (blob name, generation). A GCS
# generation changes whenever an object is rewritten, so a cached count is
# valid for as long as the blob list still shows that generation.
_chunk_count_cache: dict[tuple[str, int], int] = {}
_chunk_count_lock = threading.Lock()


def count_vectorized_content() -> int:
    """Count total content elements (chunks) across all vectorized JSON files.

    Each JSON file in ftd-vectorized-data represents one SEC filing and contains
    a 'chunks' array with text preview + embedding pairs. This function sums
    the chunk counts across all files to report the total number of content
    elements (articles) available for search and retrieval.

    The blob list is fetched on every call (~0.1s), but each file is downloaded
    only the first time its (name, generation) is seen; later calls reuse the
    cached count. New or rewritten files are picked up on the next call, and
    deleted files drop out because only blobs in the current list are summed.
    """
    import concurrent.futures

    client = _get_client()
    bucket = client.bucket(_BUCKET)

    all_blobs: list[storage.Blob] = []
    for form_dir in _SEC_FORMS:
        for blob in bucket.list_blobs(prefix=f"{form_dir}/"):
            if blob.name.endswith(".json"):
                all_blobs.append(blob)

    def _count_chunks(blob: storage.Blob) -> int | None:
        try:
            data = blob.download_as_bytes()
            parsed = json.loads(data.decode("utf-8"))
            return len(parsed.get("chunks", []))
        except Exception:
            return None

    keys = [(blob.name, blob.generation or 0) for blob in all_blobs]

    # Serialize so concurrent cold requests don't each download every file.
    with _chunk_count_lock:
        missing = [(key, blob) for key, blob in zip(keys, all_blobs) if key not in _chunk_count_cache]
        if missing:
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                counts = executor.map(_count_chunks, [blob for _, blob in missing])
                for (key, _), count in zip(missing, counts):
                    # Failed downloads count as 0 now (as before) but aren't
                    # cached, so they're retried on the next call.
                    if count is not None:
                        _chunk_count_cache[key] = count

        current = set(keys)
        for key in [k for k in _chunk_count_cache if k not in current]:
            del _chunk_count_cache[key]

        return sum(_chunk_count_cache.get(key, 0) for key in keys)


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
    """Get SEC timeline events from vectorized GCS data.

    Returns TimelineEvent objects with source='sec' for filings in the date range.
    """
    cik = _resolve_ticker_to_cik(ticker)
    if cik is None:
        logger.info("ticker_cik_not_found: ticker=%s", ticker)
        return []

    cik_clean = cik.replace("-", "").zfill(10)
    results: list[TimelineEvent] = []

    for form_dir in _SEC_FORMS:
        form_type = "8-K" if form_dir == "sec-8k" else "10-K"
        prefix = f"{form_dir}/{cik_clean}/"
        for blob in _list_vectorized_blobs(prefix):
            try:
                parsed = _download_filing_json(blob)
            except Exception:
                continue

            meta = parsed.get("sec_metadata", {})
            filing_date = _parse_date(meta.get("filing_date"))
            if filing_date is None:
                continue

            if filing_date < start or filing_date > end:
                continue

            accession = meta.get("accession_number", "")
            chunks = parsed.get("chunks", [])
            content_preview = chunks[0].get("text_preview", "") if chunks else ""

            results.append(TimelineEvent(
                normalized_calendar_date=filing_date,
                source="sec",
                element_type="narrative",
                content_body=content_preview[:200],
                current=None,
                change=None,
                form_type=form_type,
                item_number="N/A",
                date_precision=None,
            ))

    results.sort(key=lambda x: x.normalized_calendar_date or date.min, reverse=True)
    return results[offset:offset + limit]


def get_fiscal_year_end_from_gcs(ticker: str) -> FiscalYearEnd | None:
    """Get fiscal year end from the fiscal_parameters table.

    Resolution flow:
      1. Resolve ticker → CIK (via _resolve_ticker_to_cik, which tries
         PostgreSQL then GCS fallback)
      2. Query fiscal_parameters by CIK
      3. Construct FiscalYearEnd response

    Note: the old deprecated function ``crud.get_ticker_fiscal_year_end``
    joined ``staging_sec`` on CIK — the new implementation resolves CIK
    independently and queries ``fiscal_parameters`` directly.
    """
    from app.db import query_dict

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
