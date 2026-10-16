#!/usr/bin/env python3
"""Correct target_cik in staging_finnhub / staging_gnews (CLAUDE.md known issue #9).

The old lakehouse loader shifted ticker -> CIK pairs. The trusted map comes
from SEC filing paths in GCS (load_gcs_ticker_cik_map in sync_recent_relational).

Default is a dry run: per table, count rows whose CIK is correct, wrong (or
NULL) for a ticker the map knows, or unverifiable (ticker not in the map).

--apply, per table and in one transaction:
  1. CREATE TABLE {table}_cik_backup_{YYYYMMDD} AS a full copy (restore by
     replacing the table's rows from it; drop it once verified)
  2. UPDATE target_cik from the map where it differs
  3. with --null-unverified, also set target_cik NULL for tickers the map
     doesn't know (a missing CIK instead of a possibly-wrong one)

Uses the PG* environment (on the API VM, take it from the ftd-api unit as
scripts/sync_all_recent.sh does).

Usage:
    python3 scripts/fix_staging_ciks.py                 # dry run
    python3 scripts/fix_staging_ciks.py --apply [--null-unverified]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from google.cloud import storage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_recent_relational import RAW_BUCKET, load_gcs_ticker_cik_map  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fix_staging_ciks")

TABLES = ("staging_finnhub", "staging_gnews")


def _connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "10.168.0.3"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "ftd_lakehouse_staging"),
        user=os.environ.get("PGUSER", "ftd_app"),
        password=os.environ["PGPASSWORD"],
    )


def _load_map_table(cur, cik_map: dict[str, str]) -> None:
    cur.execute("CREATE TEMP TABLE cik_map (ticker TEXT PRIMARY KEY, cik TEXT NOT NULL) ON COMMIT DROP")
    psycopg2.extras.execute_values(cur, "INSERT INTO cik_map (ticker, cik) VALUES %s", sorted(cik_map.items()))


def _counts(cur, table: str) -> dict[str, int]:
    cur.execute(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE m.ticker IS NOT NULL AND t.target_cik = m.cik)                AS correct,
            COUNT(*) FILTER (WHERE m.ticker IS NOT NULL AND t.target_cik IS DISTINCT FROM m.cik) AS wrong_or_null,
            COUNT(*) FILTER (WHERE m.ticker IS NULL AND t.target_cik IS NOT NULL)                AS unverifiable,
            COUNT(*) FILTER (WHERE m.ticker IS NULL AND t.target_cik IS NULL)                    AS unknown_null,
            COUNT(DISTINCT t.target_ticker) FILTER (WHERE m.ticker IS NOT NULL AND t.target_cik IS DISTINCT FROM m.cik) AS tickers_to_fix
        FROM {table} t
        LEFT JOIN cik_map m ON m.ticker = upper(t.target_ticker)
        """
    )
    return dict(zip(("correct", "wrong_or_null", "unverifiable", "unknown_null", "tickers_to_fix"), cur.fetchone()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="back up each table, then update CIKs")
    parser.add_argument("--null-unverified", action="store_true", help="also NULL CIKs of tickers the map doesn't know")
    args = parser.parse_args()

    cik_map = load_gcs_ticker_cik_map(storage.Client().bucket(RAW_BUCKET))
    logger.info("Trusted map from GCS filing paths: %d tickers", len(cik_map))
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d")

    conn = _connect()
    try:
        for table in TABLES:
            with conn.cursor() as cur:
                _load_map_table(cur, cik_map)
                before = _counts(cur, table)
                logger.info("%s before: %s", table, before)
                if not args.apply:
                    conn.rollback()
                    continue

                backup = f"{table}_cik_backup_{suffix}"
                cur.execute(f"CREATE TABLE {backup} AS TABLE {table}")
                logger.info("%s: backed up %d rows to %s", table, cur.rowcount, backup)
                cur.execute(
                    f"""
                    UPDATE {table} t SET target_cik = m.cik
                    FROM cik_map m
                    WHERE m.ticker = upper(t.target_ticker) AND t.target_cik IS DISTINCT FROM m.cik
                    """
                )
                logger.info("%s: corrected %d rows", table, cur.rowcount)
                if args.null_unverified:
                    cur.execute(
                        f"""
                        UPDATE {table} t SET target_cik = NULL
                        WHERE t.target_cik IS NOT NULL
                          AND NOT EXISTS (SELECT 1 FROM cik_map m WHERE m.ticker = upper(t.target_ticker))
                        """
                    )
                    logger.info("%s: cleared %d unverifiable CIKs", table, cur.rowcount)
                after = _counts(cur, table)
                logger.info("%s after: %s", table, after)
                if after["wrong_or_null"]:
                    raise RuntimeError(f"{table}: {after['wrong_or_null']} rows still disagree with the map; rolled back")
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
