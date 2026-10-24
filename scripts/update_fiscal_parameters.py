#!/usr/bin/env python3
"""Keep fiscal_parameters current from the newest 10-K per CIK (insert-only).

The fiscal year end is the period of report, which the 10-K's primary document
name carries: SEC/10-K/{CIK}/{accession}/aapl-20250927.htm -> 2025-09-27. The
name is read from the sec_vectorized_chunks mirror, which the nightly sync fills
from the same ftd-vectorized-data objects.

For each CIK with a 10-K: a row is added when the CIK has no row yet or when the
newest 10-K's date differs from its latest row. Before a row is added, the
filing's cover-page dei:DocumentPeriodEndDate (read from the raw 10-K in
gs://raw-data-strg) must agree with the name's date. A CIK is skipped, never
inserted, when the two disagree, when the XBRL value cannot be read, or when the
date is outside 2000-01-01..today; skips are logged with both values.

Existing rows are never changed or deleted, and the endpoint reads the latest row
per CIK. Run nightly by sync_all_recent.sh. Uses the PG* env.

Usage: python3 scripts/update_fiscal_parameters.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import re
from datetime import date, datetime, timezone

import psycopg2
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_BUCKET = "raw-data-strg"
_PERIOD = re.compile(r"(?<!\d)((?:19|20)\d{6})(?!\d)")
_XBRL_PERIOD = re.compile(
    r'<ix:nonNumeric[^>]*name="dei:DocumentPeriodEndDate"[^>]*>(.*?)</ix:nonNumeric>',
    re.IGNORECASE | re.DOTALL,
)
_HEADER_END = re.compile(rb"</ix:header>", re.IGNORECASE)
_HEADER_READ_CHUNK = 256 * 1024
_HEADER_READ_MAX = 8 * 1024 * 1024
_EARLIEST_PLAUSIBLE = date(2000, 1, 1)
_XBRL_DATE_FORMATS = ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d")
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


def plausible(fye: str, today: date) -> bool:
    """True when the date is between 2000-01-01 and today, inclusive."""
    return _EARLIEST_PLAUSIBLE <= date.fromisoformat(fye) <= today


def xbrl_period_text(html: str) -> str | None:
    """The text of dei:DocumentPeriodEndDate in the filing's inline XBRL header, tags removed."""
    match = _XBRL_PERIOD.search(html)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1)).replace("&#160;", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip() or None


def xbrl_period_end(text: str) -> str | None:
    """'December 27, 2025' or '12/28/2025' -> ISO date; None when there is no full date (e.g. no year)."""
    for fmt in _XBRL_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def verify_period(html: str | None, want: str) -> tuple[str, str]:
    """Compare the filing's cover-page period with the name's date (the year from the name when the tag has none).

    Returns (status, xbrl_text): status is 'agree', 'disagree' or 'unreadable'.
    """
    if not html:
        return "unreadable", ""
    text = xbrl_period_text(html)
    if text is None:
        return "unreadable", ""
    # Most filings put only month and day in this tag ("December 31"); the year is then the
    # name's year, so the check is month and day against the name.
    if re.search(r"\d{4}", text):
        got = xbrl_period_end(text)
    else:
        got = xbrl_period_end(f"{text}, {want[:4]}")
    if got is None:
        return "unreadable", text
    return ("agree" if got == want else "disagree"), text


def fetch_filing_header(source_object: str) -> str | None:
    """Read the raw 10-K from its start up to </ix:header> (the cover-page XBRL lives there)."""
    try:
        buf = bytearray()
        with storage.Client().bucket(RAW_BUCKET).blob(source_object).open("rb") as f:
            while len(buf) < _HEADER_READ_MAX:
                chunk = f.read(_HEADER_READ_CHUNK)
                if not chunk:
                    break
                buf += chunk
                if _HEADER_END.search(buf):
                    break
        return buf.decode("utf-8", "replace")
    except Exception as exc:  # missing or unreadable raw file: the CIK is skipped, not guessed
        logger.warning("could not read raw 10-K gs://%s/%s: %s", RAW_BUCKET, source_object, exc)
        return None


def plan_updates(newest: dict[str, tuple[str, str]], latest: dict[str, str]) -> list[tuple[str, str, str]]:
    """(cik, fiscal_year_end_date, accession) for each CIK whose newest 10-K gives a date not in its latest row.

    newest: cik -> (accession, fiscal_year_end_date); latest: cik -> latest fiscal_year_end_date.
    """
    return [(cik, fye, acc) for cik, (acc, fye) in sorted(newest.items()) if latest.get(cik) != fye]


def run(conn, dry_run: bool = False, fetch=fetch_filing_header) -> dict[str, list]:
    """Plan the new rows, check each against its filing, and unless dry_run insert the ones that pass.

    Returns {"insert": [(cik, fye, accession)], "disagree": [...], "unreadable": [...], "implausible": [...]}.
    Skipped entries are (cik, fye, accession, detail).
    """
    today = date.today()
    result: dict[str, list] = {"insert": [], "disagree": [], "unreadable": [], "implausible": []}
    with conn.cursor() as cur:
        cur.execute(NEWEST_10K_SQL)
        newest: dict[str, tuple[str, str]] = {}
        sources: dict[str, str] = {}
        unparsed = 0
        for cik, accession, source_object in cur.fetchall():
            fye = period_end(source_object)
            if fye is None:
                unparsed += 1
                logger.warning("no period in 10-K name, skipped: %s", source_object)
                continue
            newest[cik.zfill(10)] = (accession, fye)
            sources[cik.zfill(10)] = source_object

        cur.execute(LATEST_ROW_SQL)
        latest = dict(cur.fetchall())
        plan = plan_updates(newest, latest)
        missing = sum(1 for cik, _, _ in plan if cik not in latest)
        logger.info("fiscal parameters: %d CIKs with a 10-K period (%d unparsed); %d new rows (%d missing, %d changed)",
                    len(newest), unparsed, len(plan), missing, len(plan) - missing)

        for cik, fye, accession in plan:
            if not plausible(fye, today):
                result["implausible"].append((cik, fye, accession, "outside 2000-01-01..today"))
                logger.warning("skipped (implausible date): cik=%s date=%s accession=%s", cik, fye, accession)
                continue
            status, xbrl_text = verify_period(fetch(sources[cik]), fye)
            if status == "agree":
                result["insert"].append((cik, fye, accession))
                continue
            key = "disagree" if status == "disagree" else "unreadable"
            detail = f"xbrl={xbrl_text!r}" if xbrl_text else "xbrl=(not found)"
            result[key].append((cik, fye, accession, detail))
            logger.warning("skipped (XBRL %s): cik=%s filename=%s %s accession=%s",
                           status, cik, fye, detail, accession)

        skipped = len(result["disagree"]) + len(result["unreadable"]) + len(result["implausible"])
        logger.info("fiscal parameters: would insert %d; skipped %d (XBRL disagrees %d, XBRL unreadable %d, implausible %d)",
                    len(result["insert"]), skipped, len(result["disagree"]), len(result["unreadable"]),
                    len(result["implausible"]))
        if dry_run:
            for cik, fye, accession in result["insert"]:
                print(f"INSERT  {cik}  {fye}  {accession}  (was {latest.get(cik, '-')})")
            for cik, fye, accession, detail in result["disagree"] + result["unreadable"] + result["implausible"]:
                print(f"SKIP    {cik}  {fye}  {accession}  {detail}")
            print(f"skipped: {skipped} (disagree {len(result['disagree'])}, unreadable {len(result['unreadable'])}, "
                  f"implausible {len(result['implausible'])})")
            return result

        extracted_at = datetime.now(timezone.utc).isoformat()
        for cik, fye, accession in result["insert"]:
            cur.execute(INSERT_SQL, (cik, fye, accession.replace("-", ""), extracted_at))
    conn.commit()
    logger.info("fiscal parameters: inserted %d rows", len(result["insert"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with psycopg2.connect("") as conn:
        run(conn, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
