#!/usr/bin/env python3
"""Sync vectorized SEC data from GCS (ftd-vectorized-data) into PostgreSQL.

Non-destructive: uses INSERT ... ON CONFLICT (source_object, chunk_index) 
DO NOTHING to avoid overwriting or duplicating existing records.

Designed to be run as a periodic cron job to keep PostgreSQL in sync with GCS.

Usage:
    python3 scripts/sync_vectorized_to_postgres.py
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import storage
import psycopg2
from psycopg2.extras import execute_values, Json

# Add app to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_connection


BUCKET = os.environ.get("GCS_VECTORIZED_BUCKET", "ftd-vectorized-data")
SEC_FORMS = ["sec-8k", "sec-10k", "sec-10q", "sec-10k", "sec-8k"]
BATCH_SIZE = 500
MAX_WORKERS = 10


def list_all_blobs():
    """List all JSON blobs in the vectorized bucket."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blobs = []
    for blob in bucket.list_blobs():
        if blob.name.endswith(".json"):
            blobs.append(blob)
    return blobs


def process_blob(blob):
    """Download and parse a vectorized JSON file, return list of chunk dicts."""
    try:
        data = json.loads(blob.download_as_bytes().decode("utf-8"))
    except Exception as e:
        print(f"ERROR downloading {blob.name}: {e}")
        return []

    sec_meta = data.get("sec_metadata", {})
    chunks = data.get("chunks", [])

    records = []
    for chunk in chunks:
        records.append({
            "ticker": sec_meta.get("ticker"),
            "cik": sec_meta.get("cik"),
            "accession_number": sec_meta.get("accession_number"),
            "form_type": sec_meta.get("form"),
            "filing_date": sec_meta.get("filing_date"),
            "chunk_index": chunk.get("chunk_index", 0),
            "text_preview": chunk.get("text_preview", ""),
            "vector": json.dumps(chunk.get("vector", [])),
            "source_bucket": data.get("source_bucket"),
            "source_object": data.get("source_object"),
            "vectorized_at": data.get("vectorized_at"),
        })
    return records


def sync():
    """Main sync function."""
    blobs = list_all_blobs()
    print(f"Found {len(blobs)} JSON files in GCS bucket '{BUCKET}'")

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    # Process files concurrently
    all_records = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_blob, blob): blob for blob in blobs}
        for future in as_completed(futures):
            blob = futures[future]
            try:
                records = future.result()
                all_records.extend(records)
            except Exception as e:
                print(f"ERROR processing {blob.name}: {e}")
                total_errors += 1

    print(f"Parsed {len(all_records)} total chunks from {len(blobs)} files")

    # Insert in batches using execute_values for speed
    insert_sql = """
        INSERT INTO sec_vectorized_chunks 
            (ticker, cik, accession_number, form_type, filing_date, 
             chunk_index, text_preview, vector, source_bucket, 
             source_object, vectorized_at)
        VALUES %s
        ON CONFLICT (source_object, chunk_index) DO NOTHING
    """
    
    with get_connection() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            for i in range(0, len(all_records), BATCH_SIZE):
                batch = all_records[i:i + BATCH_SIZE]
                values = [
                    (
                        r["ticker"], r["cik"], r["accession_number"], r["form_type"],
                        r["filing_date"], r["chunk_index"], r["text_preview"],
                        r["vector"],
                        r["source_bucket"], r["source_object"], r["vectorized_at"],
                    )
                    for r in batch
                ]
                try:
                    execute_values(cur, insert_sql, values, page_size=100)
                    conn.commit()
                    total_inserted += len(batch)
                    print(f"Progress: {total_inserted} inserted (batch {i//BATCH_SIZE + 1}, {len(all_records)} total)")
                except Exception as e:
                    conn.rollback()
                    total_errors += len(batch)
                    print(f"ERROR in batch {i//BATCH_SIZE + 1}: {e}, rolled back")

    # Report final state
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sec_vectorized_chunks")
            total_rows = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT source_object) FROM sec_vectorized_chunks")
            total_files = cur.fetchone()[0]

    print(f"\n=== Sync Complete ===")
    print(f"Total chunks in PostgreSQL: {total_rows}")
    print(f"Total unique files: {total_files}")
    print(f"Files processed from GCS: {len(blobs)}")


if __name__ == "__main__":
    sync()
