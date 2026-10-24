#!/usr/bin/env python3
"""Keep fiscal_parameters current from the newest 10-K per CIK (insert-only).

The fiscal year end is the period of report, which the 10-K's primary document
name carries: SEC/10-K/{CIK}/{accession}/aapl-20250927.htm -> 2025-09-27. The
vectorized metadata (sec_metadata, metadata.txt) has no period field, so the
name is the source. It is read from the sec_vectorized_chunks mirror, which the
nightly sync fills from the same ftd-vectorized-data objects.

For each CIK with a 10-K: a row is added when the CIK has no row yet or when the
newest 10-K's date differs from its latest row. Existing rows are never changed
or deleted, and the endpoint reads the latest row per CIK. Run nightly by
sync_all_recent.sh. Uses the PG* env.

Usage: python3 scripts/update_fiscal_parameters.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import datetime, timezone

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_PERIOD = re.compile(r"(?<!\d)((?:19|20)\d{6})(?!\d)")
NEWEST_10K_SQL = """
    SELECT DISTINCT ON (cik) cik, accession_number, source_object
    FROM sec_vectorized_chunks
    WHERE form_type = '10-K' AND cik IS NOT NULL
    ORDER BY cik, filing_date DESC NULLS LAST, accession_number DESC
"""
LATEST_ROW_SQL = """
    SELECT DISTINCT ON (target_cik) target_cik, fiscal_year_end_date
    FROM fiscal_parameters
    ORDER BY target_cik, extracted_at DESC NULLS LAST, fiscal_year_end_date DESC
"""
INSERT_SQL = """
    INSERT INTO fiscal_parameters (target_cik, fiscal_year_end_date, source_accession, extracted_at)
    VALUES (%s, %s, %s, %s)
"""


def period_end(source_object: str) -> str | None:
    """'SEC/10-K/0000320193/000032019325000079/aapl-20250927.htm' -> '2025-09-27'; None if no valid date."""
    match = _PERIOD.search((source_object or "").rsplit("/", 1)[-1])
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def plan_updates(newest: dict[str, tuple[str, str]], latest: dict[str, str]) -> list[tuple[str, str, str]]:
    """(cik, fiscal_year_end_date, accession) for each CIK whose newest 10-K gives a date not in its latest row.

    newest: cik -> (accession, fiscal_year_end_date); latest: cik -> latest fiscal_year_end_date.
    """
    return [(cik, fye, acc) for cik, (acc, fye) in sorted(newest.items()) if latest.get(cik) != fye]


def run(conn, dry_run: bool = False) -> list[tuple[str, str, str]]:
    """Plan the new rows and, unless dry_run, insert them. Returns the plan."""
    with conn.cursor() as cur:
        cur.execute(NEWEST_10K_SQL)
        newest: dict[str, tuple[str, str]] = {}
        unparsed = 0
        for cik, accession, source_object in cur.fetchall():
            fye = period_end(source_object)
            if fye is None:
                unparsed += 1
                logger.warning("no period in 10-K name, skipped: %s", source_object)
                continue
            newest[cik.zfill(10)] = (accession, fye)

        cur.execute(LATEST_ROW_SQL)
        latest = dict(cur.fetchall())
        plan = plan_updates(newest, latest)
        missing = sum(1 for cik, _, _ in plan if cik not in latest)
        logger.info("fiscal parameters: %d CIKs with a 10-K period (%d unparsed); %d new rows (%d missing, %d changed)",
                    len(newest), unparsed, len(plan), missing, len(plan) - missing)
        if dry_run:
            for cik, fye, accession in plan:
                print(f"{cik}  {fye}  {accession}  (was {latest.get(cik, '-')})")
            return plan

        extracted_at = datetime.now(timezone.utc).isoformat()
        for cik, fye, accession in plan:
            cur.execute(INSERT_SQL, (cik, fye, accession.replace("-", ""), extracted_at))
    conn.commit()
    logger.info("fiscal parameters: inserted %d rows", len(plan))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with psycopg2.connect("") as conn:
        run(conn, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
