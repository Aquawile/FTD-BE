#!/usr/bin/env python3
"""Remove duplicate news rows from staging_gnews (CLAUDE.md known issue #8).

A duplicate is a repeat of (target_ticker, url — or the first 200 chars of the
body when url is NULL, calendar date): the same key scripts/sync_recent_relational.py
uses to skip existing rows. The old lakehouse loader wrote one row per daily GNews
fetch of the same article.

Default is a dry run (counts only). --apply, in one transaction:
  1. copies the rows to be deleted into staging_gnews_dupes_backup_YYYYMMDD
  2. deletes them, keeping the first physical row (lowest ctid) of each group
  3. rolls back if any duplicate group remains

Uses the PG* environment (on the API VM, take it from the ftd-api unit).

Usage:
    python3 scripts/dedupe_staging_gnews.py [--apply]
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dedupe_staging_gnews")

_KEY = "target_ticker, COALESCE(url, LEFT(content_body, 200)), normalized_calendar_date::date"
_EXTRA_ROWS = f"""
    SELECT ctid FROM (
        SELECT ctid, ROW_NUMBER() OVER (PARTITION BY {_KEY} ORDER BY ingest_date NULLS LAST, ctid) AS rn
        FROM staging_gnews
    ) ranked
    WHERE rn > 1
"""


def _connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "10.168.0.3"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "ftd_lakehouse_staging"),
        user=os.environ.get("PGUSER", "ftd_app"),
        password=os.environ["PGPASSWORD"],
    )


def _counts(cur) -> tuple[int, int]:
    cur.execute(f"SELECT COUNT(*), COALESCE(SUM(n - 1), 0) FROM (SELECT COUNT(*) n FROM staging_gnews GROUP BY {_KEY} HAVING COUNT(*) > 1) d")
    groups, extra = cur.fetchone()
    return int(groups), int(extra)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = _connect()
    try:
        with conn.cursor() as cur:
            groups, extra = _counts(cur)
            logger.info("duplicate groups: %d, extra rows: %d", groups, extra)
            if not args.apply or extra == 0:
                conn.rollback()
                return 0
            backup = f"staging_gnews_dupes_backup_{datetime.now(timezone.utc):%Y%m%d}"
            cur.execute(f"CREATE TABLE {backup} AS SELECT * FROM staging_gnews WHERE ctid IN ({_EXTRA_ROWS})")
            logger.info("backed up %d rows to %s", cur.rowcount, backup)
            cur.execute(f"DELETE FROM staging_gnews WHERE ctid IN ({_EXTRA_ROWS})")
            logger.info("deleted %d rows", cur.rowcount)
            groups_after, extra_after = _counts(cur)
            if extra_after:
                raise RuntimeError(f"{groups_after} duplicate groups remain; rolled back")
        conn.commit()
        logger.info("done: 0 duplicate groups remain")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
