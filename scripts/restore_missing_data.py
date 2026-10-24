#!/usr/bin/env python3
"""Insert-only restore of pipeline data that exists in storage but not in Postgres.

Never deletes, updates or truncates anything, and adds a row only when no
equivalent row is already there, so it is safe to run more than once. Without
--apply every step runs read-only and reports how many rows it WOULD add.

Sources (all produced by the pipelines since June 2026):
  news_backup   staging_gnews_dupes_backup_20261016  -> staging_gnews
                (the 1,580 rows removed on 2026-10-16; guarded by a row count so it can't run twice)
  news          lakehouse snapshots (Jul 17, Sep 18)  -> staging_gnews
  prices        lakehouse snapshots                   -> staging_finnhub
  sec           lakehouse snapshots                   -> staging_sec_archive
  unified       lakehouse snapshots (Jul 17 + Sep 18) -> unified_staging_archive (must be empty)
The raw daily folders (prices/, gnews/ in raw-data-strg) are loaded by the existing
scripts/sync_recent_relational.py --since <date>, which is also insert-only.

Snapshots are read from /tmp/snap/{jul17,sep18}/<table>.parquet (downloaded from
gs://raw-data-strg/lakehouse/staging and gs://processed-layer-one/lakehouse/staging).
Uses the PG* environment.

Usage: restore_missing_data.py [--apply] [--steps news_backup,news,prices,sec,unified]
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

import psycopg2
import pyarrow.parquet as pq

SNAP_DIR = os.environ.get("SNAP_DIR", "/tmp/snap")
GENERATIONS = ("jul17", "sep18")           # oldest first
DUPES_BACKUP = "staging_gnews_dupes_backup_20261016"
# staging_gnews rows with ingest_date 2026-09-18 before / after the Oct 16 dedupe
GNEWS_SEP18_ORIGINAL = 9840
GNEWS_DEDUPED = 1580


EXPECTED_DB = "ftd_lakehouse_staging"
# The only tables this script may write to: the RELATIONAL archive/staging tables.
# sec_vectorized_chunks (the mirror of the vectorized bucket) is never written here.
WRITABLE = {"staging_gnews", "staging_finnhub", "staging_sec_archive", "unified_staging_archive"}


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def table_columns(cur, table: str) -> list[str]:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
    return [r[0] for r in cur.fetchall()]


def load_temp(cur, tmp: str, like: str, parquet: str, cols: list[str]) -> tuple[int, list[str]]:
    """COPY a parquet snapshot into a temp table shaped like `like`. Returns (rows, columns loaded)."""
    pf = pq.ParquetFile(parquet)
    use = [c for c in cols if c in pf.schema_arrow.names]
    cur.execute(f"CREATE TEMP TABLE {tmp} (LIKE {like} INCLUDING DEFAULTS) ON COMMIT DROP")
    sql = f"COPY {tmp} ({', '.join(use)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')"
    for batch in pf.iter_batches(batch_size=40_000, columns=use):
        buf = io.StringIO()
        batch.to_pandas().to_csv(buf, index=False, header=False, na_rep="\\N")
        buf.seek(0)
        cur.copy_expert(sql, buf)
    cur.execute(f"SELECT COUNT(*) FROM {tmp}")
    return cur.fetchone()[0], use


def blanks_to_null(cur, tmp: str, table: str, cols: list[str]) -> None:
    """The existing archive rows store empty text as NULL (the snapshots hold ''), so do the same."""
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND data_type='text'", (table,))
    text_cols = [r[0] for r in cur.fetchall() if r[0] in cols]
    if text_cols:
        cur.execute(f"UPDATE {tmp} SET " + ", ".join(f"{c} = NULLIF({c}, '')" for c in text_cols))


def row_hash(alias: str, cols: list[str]) -> str:
    return f"md5(ROW({', '.join(f'{alias}.{c}' for c in cols)})::text)"


def keyed(table_or_sub: str, cols: list[str]) -> str:
    """SELECT of (hash, occurrence) per row: the k-th identical row gets k, so duplicates count."""
    return (f"SELECT {row_hash('x', cols)} AS h, ROW_NUMBER() OVER (PARTITION BY {row_hash('x', cols)}) AS k "
            f"FROM {table_or_sub} x")


def check_target(table: str) -> None:
    if table not in WRITABLE:
        raise SystemExit(f"refusing to write to {table}: not a relational target")


def step_news_backup(cur, apply: bool) -> int:
    cur.execute("SELECT COUNT(*) FROM staging_gnews WHERE ingest_date::date = '2026-09-18'")
    now_n = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {DUPES_BACKUP}")
    backup_n = cur.fetchone()[0]
    log(f"news_backup: Sep-18 batch has {now_n:,} rows now (original {GNEWS_SEP18_ORIGINAL:,}); backup holds {backup_n:,}")
    if now_n != GNEWS_SEP18_ORIGINAL - GNEWS_DEDUPED or backup_n != GNEWS_DEDUPED:
        log("  skipped: counts don't match the pre-restore state (already restored, or changed since)")
        return 0
    cols = table_columns(cur, "staging_gnews")
    check_target("staging_gnews")
    if apply:
        cur.execute(f"INSERT INTO staging_gnews ({', '.join(cols)}) SELECT {', '.join(cols)} FROM {DUPES_BACKUP}")
        n = cur.rowcount
    else:
        n = backup_n
    log(f"  {'inserted' if apply else 'would insert'} {n:,}")
    return n


def step_news(cur, apply: bool) -> int:
    check_target("staging_gnews")
    cols = table_columns(cur, "staging_gnews")
    total = 0
    for gen in GENERATIONS:
        path = f"{SNAP_DIR}/{gen}/staging_gnews.parquet"
        rows, use = load_temp(cur, f"t_gnews_{gen}", "staging_gnews", path, cols)
        log(f"news[{gen}]: {rows:,} rows in snapshot")
        # equivalent = same ticker, same day, same text (snapshots from before ~Sep 2026 carry no url)
        sel = (f"FROM t_gnews_{gen} t LEFT JOIN (SELECT target_ticker, normalized_calendar_date::date d, md5(content_body) h "
               f"FROM staging_gnews GROUP BY 1, 2, 3) e ON e.target_ticker = t.target_ticker "
               f"AND e.d = t.normalized_calendar_date::date AND e.h = md5(t.content_body) WHERE e.h IS NULL")
        if apply:
            cur.execute(f"INSERT INTO staging_gnews ({', '.join(use)}) SELECT {', '.join('t.' + c for c in use)} {sel}")
            n = cur.rowcount
        else:
            cur.execute(f"SELECT COUNT(*) {sel}")
            n = cur.fetchone()[0]
        log(f"  {'inserted' if apply else 'would insert'} {n:,}")
        total += n
    return total


def step_prices(cur, apply: bool) -> int:
    check_target("staging_finnhub")
    cols = table_columns(cur, "staging_finnhub")
    total = 0
    for gen in GENERATIONS:
        path = f"{SNAP_DIR}/{gen}/staging_finnhub.parquet"
        rows, use = load_temp(cur, f"t_fh_{gen}", "staging_finnhub", path, cols)
        log(f"prices[{gen}]: {rows:,} rows in snapshot")
        sel = (f"FROM t_fh_{gen} t LEFT JOIN (SELECT DISTINCT target_ticker, normalized_calendar_date::date d FROM staging_finnhub) e "
               f"ON e.target_ticker = t.target_ticker AND e.d = t.normalized_calendar_date::date WHERE e.d IS NULL")
        if apply:
            cur.execute(f"INSERT INTO staging_finnhub ({', '.join(use)}) SELECT {', '.join('t.' + c for c in use)} {sel}")
            n = cur.rowcount
        else:
            cur.execute(f"SELECT COUNT(*) {sel}")
            n = cur.fetchone()[0]
        log(f"  {'inserted' if apply else 'would insert'} {n:,}")
        total += n
    return total


def step_sec(cur, apply: bool) -> int:
    """A SEC element is the same row if filing, item and text match (element_id is a random UUID per run).
    Identical rows are counted, so a repeated paragraph in the snapshot is only skipped as often as it exists."""
    check_target("staging_sec_archive")
    cols = table_columns(cur, "staging_sec_archive")
    ident = "t.accession_number, COALESCE(t.item_number, ''), md5(COALESCE(t.content_body, ''))"
    ident_e = ident.replace("t.", "x.")
    total = 0
    for gen in GENERATIONS:
        path = f"{SNAP_DIR}/{gen}/staging_sec.parquet"
        tmp = f"t_sec_{gen}"
        rows, use = load_temp(cur, tmp, "staging_sec_archive", path, cols)
        blanks_to_null(cur, tmp, "staging_sec_archive", use)
        log(f"sec[{gen}]: {rows:,} rows in snapshot")
        sel = (f"FROM (SELECT t.*, md5(ROW({ident})::text) AS h, ROW_NUMBER() OVER (PARTITION BY {ident}) AS k FROM {tmp} t) t "
               f"LEFT JOIN (SELECT md5(ROW({ident_e})::text) AS h, ROW_NUMBER() OVER (PARTITION BY {ident_e}) AS k FROM staging_sec_archive x) e "
               f"ON e.h = t.h AND e.k = t.k WHERE e.h IS NULL")
        if apply:
            cur.execute(f"INSERT INTO staging_sec_archive ({', '.join(use)}) SELECT {', '.join('t.' + c for c in use)} {sel}")
            n = cur.rowcount
        else:
            cur.execute(f"SELECT COUNT(*) {sel}")
            n = cur.fetchone()[0]
        log(f"  {'inserted' if apply else 'would insert'} {n:,}")
        total += n
    return total


def step_unified(cur, apply: bool) -> int:
    """unified_staging_archive = prices + news + SEC combined. Load the Sep 18 snapshot as it was, then add
    the rows only the Jul 17 snapshot has (its older prices/news, and the 3,835 SEC rows)."""
    check_target("unified_staging_archive")
    cur.execute("SELECT COUNT(*) FROM unified_staging_archive")
    if cur.fetchone()[0] != 0:
        log("unified: unified_staging_archive is not empty; refusing to load (nothing is ever overwritten)")
        return 0
    cols = table_columns(cur, "unified_staging_archive")
    new, old = GENERATIONS[::-1]                                  # newest first: its element_ids match staging_sec_archive
    loaded: dict[str, list[str]] = {}
    for gen in (new, old):
        rows, use = load_temp(cur, f"t_uni_{gen}", "unified_staging_archive", f"{SNAP_DIR}/{gen}/unified_staging.parquet", cols)
        blanks_to_null(cur, f"t_uni_{gen}", "unified_staging_archive", use)
        loaded[gen] = use
        log(f"unified[{gen}]: {rows:,} rows in snapshot")
    # identity: SEC element = filing + item + text; price/news row = ticker + day + text
    ident = ("CASE WHEN {a}.accession_number IS NOT NULL "
             "THEN 'S|' || {a}.accession_number || '|' || COALESCE({a}.item_number, '') || '|' || md5(COALESCE({a}.content_body, '')) "
             "ELSE 'N|' || COALESCE({a}.target_ticker, '') || '|' || COALESCE({a}.normalized_calendar_date::text, '') || '|' || md5(COALESCE({a}.content_body, '')) END")
    it, ix = ident.format(a="t"), ident.format(a="x")
    only_old = (f"FROM (SELECT t.*, {it} AS id, ROW_NUMBER() OVER (PARTITION BY {it}) AS k FROM t_uni_{old} t) t "
                f"LEFT JOIN (SELECT {ix} AS id, ROW_NUMBER() OVER (PARTITION BY {ix}) AS k FROM t_uni_{new} x) e "
                f"ON e.id = t.id AND e.k = t.k WHERE e.id IS NULL")
    cur.execute(f"SELECT COUNT(*) FROM t_uni_{new}")
    n_first = cur.fetchone()[0]
    if apply:
        cur.execute(f"INSERT INTO unified_staging_archive ({', '.join(loaded[new])}) SELECT {', '.join(loaded[new])} FROM t_uni_{new}")
        a = cur.rowcount
        cur.execute(f"INSERT INTO unified_staging_archive ({', '.join(loaded[old])}) SELECT {', '.join('t.' + c for c in loaded[old])} {only_old}")
        b = cur.rowcount
    else:
        a = n_first
        cur.execute(f"SELECT COUNT(*) {only_old}")
        b = cur.fetchone()[0]
    log(f"  {'inserted' if apply else 'would insert'} {a:,} ({new}) + {b:,} ({old}, rows not in {new}) = {a + b:,}")
    return a + b


STEPS = {"news_backup": step_news_backup, "news": step_news, "prices": step_prices, "sec": step_sec, "unified": step_unified}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the rows (default: report only)")
    ap.add_argument("--steps", default=",".join(STEPS), help="comma-separated subset, run in this order")
    args = ap.parse_args()
    log(f"mode: {'APPLY (insert-only)' if args.apply else 'DRY RUN (nothing is written)'}")
    results = {}
    with psycopg2.connect("") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            db = cur.fetchone()[0]
            if db != EXPECTED_DB:
                log(f"REFUSING: connected to '{db}', expected '{EXPECTED_DB}'")
                return 2
            cur.execute("SELECT COUNT(*) FROM sec_vectorized_chunks")
            vec_before = cur.fetchone()[0]
            log(f"database: {db}; vectorized mirror sec_vectorized_chunks = {vec_before:,} rows (must stay unchanged)")
        conn.rollback()
        for name in [s.strip() for s in args.steps.split(",") if s.strip()]:
            with conn.cursor() as cur:
                t0 = time.time()
                results[name] = STEPS[name](cur, args.apply)
            conn.commit() if args.apply else conn.rollback()
            log(f"step {name} done in {time.time() - t0:.0f}s")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sec_vectorized_chunks")
            vec_after = cur.fetchone()[0]
        conn.rollback()
    log("summary: " + ", ".join(f"{k}={v:,}" for k, v in results.items()))
    if vec_after != vec_before:
        log(f"ERROR: sec_vectorized_chunks changed ({vec_before:,} -> {vec_after:,})")
        return 3
    log(f"vectorized mirror unchanged ({vec_after:,} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
