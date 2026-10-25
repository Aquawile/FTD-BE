#!/usr/bin/env python3
"""Label which stored news rows really mention the ticker they are filed under.

Until the attribution rules, every article a GNews batch returned was stored once
per ticker in that batch (~5), though it is usually about one of them. This sets
staging_gnews.attributed_by on rows that have no label yet: the rule that tied the
article to the ticker ('name', 'dollar', 'exchange', 'paren') or 'none'. Nothing
is deleted and no other column is touched; the ticker page and news search
simply skip rows labelled 'none'.

Dry run by default (read-only, prints what would be labelled). --apply writes the
labels in batches; it can be stopped and re-run, it only looks at unlabelled rows.

Run from the staging API VM next to sync_recent_relational.py (PG* env as in cron):
    python3 attribute_news.py [--apply] [--samples 8]
"""
from __future__ import annotations

import argparse
import collections
import logging
import os
import random
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_recent_relational import NOT_ATTRIBUTED, _connect, article_mentions, load_company_names  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("attribute_news")

BATCH = 5000


def label(text: str, ticker: str, names: dict[str, list[str]]) -> str:
    return article_mentions(text or "", ticker, names.get(ticker, [])) or NOT_ATTRIBUTED


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the labels (default: dry run)")
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--limit", type=int, help="with --apply: stop after labelling about this many rows (a trial run)")
    args = parser.parse_args()

    conn = _connect()
    try:
        with conn.cursor() as cur:
            names = load_company_names(cur)
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'staging_gnews' AND column_name = 'attributed_by')")
            has_column = cur.fetchone()[0]
            if args.apply and not has_column:
                raise SystemExit("staging_gnews.attributed_by does not exist yet (migration 015)")
            unlabelled = "attributed_by IS NULL" if has_column else "TRUE"
            cur.execute(f"SELECT COUNT(*) FROM staging_gnews WHERE {unlabelled}")
            todo = cur.fetchone()[0]
        logger.info("%d company names loaded; %d unlabelled rows to look at (%s)", sum(map(len, names.values())), todo,
                    "APPLY" if args.apply else "dry run")

        by_rule: collections.Counter = collections.Counter()
        by_month: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        matched_urls: set = set()
        all_urls: set = set()
        tickers_with_news: set = set()
        samples: dict[str, list] = collections.defaultdict(list)
        seen = 0
        last_ctid = None

        # Dry run walks the table once by ctid; apply repeatedly takes unlabelled rows (labelled ones drop out).
        read = conn.cursor(name="news_scan", cursor_factory=psycopg2.extras.DictCursor) if not args.apply else None
        if read is not None:
            read.itersize = BATCH
            read.execute("SELECT ctid::text AS tid, target_ticker, content_body, url, ingest_date "
                         f"FROM staging_gnews WHERE {unlabelled}")
        while True:
            if args.apply:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT ctid::text AS tid, target_ticker, content_body, url, ingest_date "
                                f"FROM staging_gnews WHERE {unlabelled} LIMIT %s", (BATCH,))
                    rows = cur.fetchall()
            else:
                rows = read.fetchmany(BATCH)
            if not rows:
                break
            updates = []
            cache: dict[tuple[str, str], str] = {}
            for r in rows:
                key = (r["target_ticker"], r["content_body"] or "")
                rule = cache.get(key) or cache.setdefault(key, label(key[1], key[0], names))
                by_rule[rule] += 1
                month = r["ingest_date"].strftime("%Y-%m") if r["ingest_date"] else "unknown"
                by_month[month][rule == NOT_ATTRIBUTED] += 1
                if r["url"]:
                    all_urls.add(r["url"])
                    if rule != NOT_ATTRIBUTED:
                        matched_urls.add(r["url"])
                if rule != NOT_ATTRIBUTED:
                    tickers_with_news.add(r["target_ticker"])
                if len(samples[rule]) < 400:
                    samples[rule].append((r["target_ticker"], (r["content_body"] or "")[:150]))
                updates.append((r["tid"], rule))
            seen += len(rows)
            if args.apply:
                with conn.cursor() as cur:
                    done = psycopg2.extras.execute_values(
                        cur,
                        "UPDATE staging_gnews g SET attributed_by = v.rule FROM (VALUES %s) AS v(tid, rule) "
                        "WHERE g.ctid = v.tid::tid AND g.attributed_by IS NULL RETURNING 1",
                        updates, page_size=1000, fetch=True)
                    if len(done) != len(updates):
                        conn.rollback()
                        raise RuntimeError(f"labelled {len(done)} of {len(updates)} rows; rolled back this batch and stopped")
                conn.commit()
                if seen % (BATCH * 10) == 0:
                    logger.info("labelled %d / %d", seen, todo)
                if args.limit and seen >= args.limit:
                    break
        if read is not None:
            read.close()
        conn.rollback()

        total = sum(by_rule.values())
        print(f"\nrows looked at: {total:,}")
        for rule, n in by_rule.most_common():
            print(f"  {rule:9s} {n:>9,}  {100 * n / max(total, 1):5.1f}%")
        print(f"distinct articles (url): {len(all_urls):,}; with at least one matching ticker: {len(matched_urls):,}; "
              f"matching none: {len(all_urls) - len(matched_urls):,}")
        print(f"tickers with at least one attributed article: {len(tickers_with_news)}")
        print("share of rows NOT about their ticker, by ingest month:")
        for month in sorted(by_month):
            c = by_month[month]
            print(f"  {month}  {c[True]:>8,} of {c[True] + c[False]:>8,}  ({100 * c[True] / max(c[True] + c[False], 1):.0f}%)")
        random.seed(7)
        for rule in sorted(samples):
            print(f"\nsamples labelled {rule!r}:")
            for ticker, text in random.sample(samples[rule], min(args.samples, len(samples[rule]))):
                print(f"  {ticker:6s} {text!r}")
        print("\nAPPLIED" if args.apply else "\ndry run: nothing written")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
