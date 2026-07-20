"""Validation core: Fortune 500 filter, fiscal date enrichment, and schema normalization."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from src.config import Settings
from src.error_logger import ErrorLogger
from src.fortune500 import fetch_target_tickers
from src.gcs_storage import GcsStorage
from src.sec_client import SecClient

logger = logging.getLogger(__name__)

_CANONICAL_COLUMNS = [
    "target_ticker",
    "target_cik",
    "element_type",
    "content_body",
    "normalized_calendar_date",
    "ingest_date",
]


def _build_cik_map(settings: LakehouseSettings) -> dict[str, str]:
    sec_settings = settings.sec_settings
    storage = GcsStorage(sec_settings)
    error_logger = ErrorLogger(settings.project_root / "error_log_validation.txt")
    sec_client = SecClient(sec_settings, error_logger)

    target_tickers = fetch_target_tickers(
        sec_client,
        storage,
        gcs_path=sec_settings.fortune_500_gcs_path,
        fallback_url=sec_settings.fortune_500_fallback_url,
        limit=settings.target_company_limit,
    )
    from src.company_roster import fetch_ticker_cik_map, resolve_target_ciks
    ticker_map = fetch_ticker_cik_map(sec_client, sec_settings.company_tickers_url)
    ciks, _ = resolve_target_ciks(target_tickers, ticker_map)
    return {t.upper(): c for t, c in zip(target_tickers, ciks)}


def _load_fiscal_map(settings: LakehouseSettings) -> dict[str, str]:
    path = f"{settings.gcs_staging_prefix}/fiscal_parameters.parquet"
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(path)
    if not blob.exists():
        logger.warning("Fiscal parameters not found at %s", path)
        return {}
    buf = blob.download_as_bytes()
    table = pq.read_table(pa.BufferReader(buf))
    df = table.to_pandas()
    return dict(zip(df["target_cik"], df["fiscal_year_end_date"]))


def _backfill_target_ticker(df: pd.DataFrame, cik_map: dict[str, str]) -> pd.DataFrame:
    inv = {v: k for k, v in cik_map.items()}
    if "target_ticker" not in df.columns:
        df["target_ticker"] = df["target_cik"].map(inv)
    else:
        missing = df["target_ticker"].isna()
        if missing.any():
            df.loc[missing, "target_ticker"] = df.loc[missing, "target_cik"].map(inv)
    return df


def _enrich_sec_dates(df: pd.DataFrame, fiscal_map: dict[str, str]) -> pd.DataFrame:
    """Resolve normalized_calendar_date and date_precision for SEC rows.

    Fallback chain (no fabrication, only real timestamps):
    10-K: period_of_report -> fiscal_year_end_date -> filing_date -> ingest_date
    8-K: filing_date -> ingest_date

    date_precision labels the source:
      exact_fiscal = period_of_report (10-K only)
      fiscal       = fiscal_year_end_date (10-K only)
      event        = filing_date (8-K or 10-K fallback)
      ingestion    = ingest_date (last resort)
    """
    if df.empty:
        return df

    df = df.copy()
    df["date_precision"] = None

    # 10-Ks
    is_10k = df["form_type"] == "10-K"
    missing_10k = is_10k & df["normalized_calendar_date"].isna()

    if missing_10k.any():
        # Priority 1: period_of_report
        has_period = missing_10k & df["period_of_report"].notna()
        if has_period.any():
            df.loc[has_period, "normalized_calendar_date"] = df.loc[has_period, "period_of_report"]
            df.loc[has_period, "date_precision"] = "exact_fiscal"

        # Priority 2: fiscal_year_end_date from fiscal_map
        still_missing = is_10k & df["normalized_calendar_date"].isna()
        if still_missing.any():
            mapped = df.loc[still_missing, "target_cik"].map(lambda c: fiscal_map.get(c))
            has_fy = still_missing & mapped.notna()
            if has_fy.any():
                df.loc[has_fy, "normalized_calendar_date"] = mapped[has_fy]
                df.loc[has_fy, "date_precision"] = "fiscal"

        # Priority 3: filing_date (real SEC metadata, not fabricated)
        still_missing = is_10k & df["normalized_calendar_date"].isna()
        if still_missing.any():
            has_filing = still_missing & df["filing_date"].notna()
            if has_filing.any():
                df.loc[has_filing, "normalized_calendar_date"] = df.loc[has_filing, "filing_date"]
                df.loc[has_filing, "date_precision"] = "event"

        # Priority 4: ingest_date (our own processing timestamp, last resort)
        still_missing = is_10k & df["normalized_calendar_date"].isna()
        if still_missing.any():
            df.loc[still_missing, "normalized_calendar_date"] = df.loc[still_missing, "ingest_date"]
            df.loc[still_missing, "date_precision"] = "ingestion"

    # 8-Ks
    is_8k = df["form_type"] == "8-K"
    missing_8k = is_8k & df["normalized_calendar_date"].isna()

    if missing_8k.any():
        # Priority 1: filing_date (8-Ks are event-based, so filing_date is the correct date)
        has_filing = missing_8k & df["filing_date"].notna()
        if has_filing.any():
            df.loc[has_filing, "normalized_calendar_date"] = df.loc[has_filing, "filing_date"]
            df.loc[has_filing, "date_precision"] = "event"

        # Priority 2: ingest_date fallback
        still_missing = is_8k & df["normalized_calendar_date"].isna()
        if still_missing.any():
            df.loc[still_missing, "normalized_calendar_date"] = df.loc[still_missing, "ingest_date"]
            df.loc[still_missing, "date_precision"] = "ingestion"

    return df


def _coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce relational-friendly types and clean nulls.

    - Replace None/NaN in object columns with empty strings (only for text columns)
    - Convert date columns to datetime64[ns] (PyArrow: timestamp[ns])
    - Convert Finnhub Unix epoch timestamp to int64
    """
    df = df.copy()

    # Convert date columns to datetime64[ns] for proper Parquet temporal types
    for col in ("normalized_calendar_date", "ingest_date", "filing_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert Finnhub ISO timestamp to datetime64[ns]
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Replace None/NaN in object columns with empty strings,
    # but skip columns that contain non-string values (e.g. Decimal prices)
    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna()
        if len(sample) > 0 and not isinstance(sample.iloc[0], str):
            continue
        df[col] = df[col].fillna("")

    return df


def validate_staging(settings: LakehouseSettings, sample: int | None = None) -> dict[str, pd.DataFrame]:
    cik_map = _build_cik_map(settings)
    fiscal_map = _load_fiscal_map(settings)
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)

    validated: dict[str, pd.DataFrame] = {}
    for table_name in ("staging_finnhub", "staging_gnews", "staging_sec"):
        path = f"{settings.gcs_staging_prefix}/{table_name}.parquet"
        blob = bucket.blob(path)
        if not blob.exists():
            logger.warning("Staging table %s not found", path)
            continue
        buf = blob.download_as_bytes()
        table = pq.read_table(pa.BufferReader(buf))
        df = table.to_pandas()

        # Fortune 500 filter
        df = df[df["target_cik"].isin(cik_map.values())].copy()

        # Backfill target_ticker from inverse CIK map
        df = _backfill_target_ticker(df, cik_map)

        # Ensure ingest_date exists
        if "ingest_date" not in df.columns:
            df["ingest_date"] = pd.Timestamp.utcnow().date().isoformat()

        # SEC-specific fiscal date enrichment
        if table_name == "staging_sec":
            df = _enrich_sec_dates(df, fiscal_map)

        # Ensure canonical columns exist (do not drop other columns)
        for col in _CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        # Coerce schema: clean nulls and convert date columns to temporal types
        df = _coerce_schema(df)

        # Reorder: canonical first, then source-specific extras
        canonical = [c for c in _CANONICAL_COLUMNS if c in df.columns]
        extras = [c for c in df.columns if c not in _CANONICAL_COLUMNS]
        df = df[canonical + extras].reset_index(drop=True)

        # Sample if requested
        if sample is not None and len(df) > sample:
            df = df.sample(n=sample, random_state=42).reset_index(drop=True)

        validated[table_name] = df
        logger.info("Validated %s: %d rows, columns=%s", table_name, len(df), list(df.columns))

    return validated


def save_validated(validated: dict[str, pd.DataFrame], settings: LakehouseSettings) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    for table_name, df in validated.items():
        path = f"{settings.gcs_staging_prefix}/{table_name}.parquet"
        df = _coerce_schema(df)
        table = pa.Table.from_pandas(df, preserve_index=False)
        blob = bucket.blob(path)
        buf = pa.BufferOutputStream()
        pq.write_table(table, buf)
        blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
        logger.info("Overwrote validated %s (%d rows)", table_name, len(df))
