"""Load lakehouse Parquet files into PostgreSQL using COPY for speed."""
import sys
from pathlib import Path
import io

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "sec"))

import pandas as pd
import psycopg2
import pyarrow.parquet as pq
import pyarrow as pa
from google.cloud import storage

from lakehouse.config import LakehouseSettings

PG_CONN = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "ftd_lakehouse",
    "user": "ftd_app",
    "password": "temp_password_123",
}

BUCKET = "processed-layer-one"
PREFIX = "lakehouse/staging"

TABLES = [
    ("staging_finnhub", "staging_finnhub.parquet"),
    ("staging_gnews", "staging_gnews.parquet"),
    ("staging_sec", "staging_sec.parquet"),
    ("unified_staging", "unified_staging.parquet"),
    ("fiscal_parameters", "fiscal_parameters.parquet"),
]


def create_tables():
    """Create PostgreSQL tables matching the BigQuery external table schemas."""
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS staging_finnhub (
      target_ticker TEXT,
      target_cik TEXT,
      element_type TEXT,
      content_body TEXT,
      normalized_calendar_date TIMESTAMP,
      ingest_date TIMESTAMP,
      symbol TEXT,
      "timestamp" TIMESTAMP,
      "current" NUMERIC,
      change NUMERIC,
      percent_change NUMERIC,
      high NUMERIC,
      low NUMERIC,
      open NUMERIC,
      previous_close NUMERIC
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS staging_gnews (
      target_ticker TEXT,
      target_cik TEXT,
      element_type TEXT,
      content_body TEXT,
      normalized_calendar_date TIMESTAMP,
      ingest_date TIMESTAMP,
      url TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS staging_sec (
      target_ticker TEXT,
      target_cik TEXT,
      element_type TEXT,
      content_body TEXT,
      normalized_calendar_date TIMESTAMP,
      ingest_date TIMESTAMP,
      element_id TEXT,
      accession_number TEXT,
      form_type TEXT,
      item_number TEXT,
      content_type TEXT,
      raw_text_string TEXT,
      period_of_report TEXT,
      filing_date TIMESTAMP,
      date_precision TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS unified_staging (
      target_ticker TEXT,
      target_cik TEXT,
      element_type TEXT,
      content_body TEXT,
      normalized_calendar_date TIMESTAMP,
      ingest_date TIMESTAMP,
      symbol TEXT,
      "timestamp" TIMESTAMP,
      "current" NUMERIC,
      change NUMERIC,
      percent_change NUMERIC,
      high NUMERIC,
      low NUMERIC,
      open NUMERIC,
      previous_close NUMERIC,
      source TEXT,
      form_type TEXT,
      element_id TEXT,
      accession_number TEXT,
      item_number TEXT,
      content_type TEXT,
      raw_text_string TEXT,
      period_of_report TEXT,
      filing_date TIMESTAMP,
      date_precision TEXT,
      url TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fiscal_parameters (
      target_cik TEXT,
      fiscal_year_end_date TEXT,
      source_accession TEXT,
      extracted_at TEXT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Tables created successfully")


def truncate_table(table_name: str):
    """Truncate table before reload to ensure idempotency."""
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
    conn.commit()
    cur.close()
    conn.close()
    print(f"Truncated {table_name}")


def load_parquet_to_postgres(table_name: str, gcs_path: str):
    """Read a Parquet file from GCS and stream it into PostgreSQL using COPY."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(gcs_path)
    buf = blob.download_as_bytes()
    table = pq.read_table(pa.BufferReader(buf))
    df = table.to_pandas()

    # Convert DataFrame to CSV in memory
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, header=False, na_rep="\\N")
    csv_data = csv_buffer.getvalue()

    # Use COPY FROM STDIN for fast bulk load
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    columns = list(df.columns)
    col_names = ", ".join([f'"{c}"' if c in ("timestamp", "current") else c for c in columns])
    copy_sql = f"COPY {table_name} ({col_names}) FROM STDIN WITH CSV NULL '\\N'"

    cur.copy_expert(copy_sql, io.StringIO(csv_data))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {len(df)} rows into {table_name}")


if __name__ == "__main__":
    create_tables()
    for table_name, file_name in TABLES:
        gcs_path = f"{PREFIX}/{file_name}"
        truncate_table(table_name)
        load_parquet_to_postgres(table_name, gcs_path)
