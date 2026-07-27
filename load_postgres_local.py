"""Load lakehouse Parquet files into PostgreSQL using local CSV files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "sec"))

import os
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
    "password": "5Ou+BkyuQT3izP72219jMLy2AobRdI3f",
}

BUCKET = "processed-layer-one"
PREFIX = "lakehouse/staging"
TMP_DIR = "/tmp/pg_load"

TABLES = [
    ("staging_finnhub", "staging_finnhub.parquet"),
    ("staging_gnews", "staging_gnews.parquet"),
    ("staging_sec", "staging_sec.parquet"),
    ("unified_staging", "unified_staging.parquet"),
    ("fiscal_parameters", "fiscal_parameters.parquet"),
]


def create_tables():
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
      ingest_date TIMESTAMP
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
      date_precision TEXT
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


def download_parquet(gcs_path: str, local_path: str):
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(local_path)
    print(f"Downloaded {gcs_path} to {local_path}")


def parquet_to_csv(parquet_path: str, csv_path: str):
    table = pq.read_table(parquet_path)
    df = table.to_pandas()
    df.to_csv(csv_path, index=False, header=True, na_rep="\\N")
    print(f"Converted {parquet_path} to {csv_path} ({len(df)} rows)")


def load_csv_to_postgres(csv_path: str, table_name: str):
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    columns = []
    with open(csv_path, "r") as f:
        header = f.readline().strip().split(",")
        columns = [c.strip('"') for c in header]

    col_names = ", ".join([f'"{c}"' if c in ("timestamp", "current") else c for c in columns])
    copy_sql = f"COPY {table_name} ({col_names}) FROM STDIN WITH CSV NULL '\\N'"

    with open(csv_path, "r") as f:
        next(f)  # skip header
        cur.copy_expert(copy_sql, f)

    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {csv_path} into {table_name}")


if __name__ == "__main__":
    os.makedirs(TMP_DIR, exist_ok=True)
    create_tables()

    for table_name, file_name in TABLES:
        gcs_path = f"{PREFIX}/{file_name}"
        parquet_path = f"{TMP_DIR}/{file_name}"
        csv_path = f"{TMP_DIR}/{table_name}.csv"

        download_parquet(gcs_path, parquet_path)
        parquet_to_csv(parquet_path, csv_path)
        load_csv_to_postgres(csv_path, table_name)

    print("All tables loaded successfully")
