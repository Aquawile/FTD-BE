"""Build a unified staging table from validated domain-specific tables."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage

from lakehouse.config import LakehouseSettings
from lakehouse.engines.validation_core import _coerce_schema
from src.gcs_storage import GcsStorage

logger = logging.getLogger(__name__)


def load_validated_table(settings: LakehouseSettings, table_name: str) -> Optional[pd.DataFrame]:
    """Load a validated Parquet table from GCS."""
    client = storage.Client(project=settings.sec_settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    path = f"{settings.gcs_staging_prefix}/{table_name}.parquet"
    blob = bucket.blob(path)
    if not blob.exists():
        logger.warning("Validated table %s not found", path)
        return None
    buf = blob.download_as_bytes()
    table = pq.read_table(pa.BufferReader(buf))
    return table.to_pandas()


def build_unified_staging(settings: LakehouseSettings) -> Optional[pd.DataFrame]:
    """Concatenate all validated staging tables into a unified relation.

    Returns a DataFrame with columns:
    target_ticker, target_cik, element_type, content_body,
    normalized_calendar_date, ingest_date, source, form_type
    """
    tables: dict[str, pd.DataFrame] = {}
    for name in ("staging_finnhub", "staging_gnews", "staging_sec"):
        df = load_validated_table(settings, name)
        if df is not None and not df.empty:
            tables[name] = df

    if not tables:
        logger.warning("No validated tables found for unified staging")
        return None

    frames = []
    for source_name, df in tables.items():
        source_label = source_name.replace("staging_", "")
        df = df.copy()
        df["source"] = source_label
        if "form_type" not in df.columns or df["form_type"].isna().all():
            df["form_type"] = ""
        frames.append(df)

    unified = pd.concat(frames, ignore_index=True)
    logger.info("Unified staging: %d rows from %d sources", len(unified), len(frames))
    return unified


def save_unified_staging(df: pd.DataFrame, settings: LakehouseSettings) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = f"{settings.gcs_staging_prefix}/unified_staging.parquet"
    df = _coerce_schema(df)
    table = pa.Table.from_pandas(df, preserve_index=False)
    storage = GcsStorage(settings.sec_settings)
    bucket = storage._bucket
    blob = bucket.blob(path)
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    blob.upload_from_string(buf.getvalue().to_pybytes(), content_type="application/octet-stream")
    logger.info("Saved unified staging (%d rows) to gs://%s/%s", len(df), settings.gcs_bucket, path)
    return path
