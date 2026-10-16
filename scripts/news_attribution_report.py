#!/usr/bin/env python3
"""Read-only report: how much of staging_gnews actually mentions its ticker (PRD-6).

Applies article_mentions() (scripts/sync_recent_relational.py) to every news row
under two name sources and prints how many rows each rule keeps. Writes nothing.

  A. names already in tickers.name (only where the name isn't just the symbol)
  B. A plus the official registrant name from each company's latest 10-K in GCS
     (raw-data-strg SEC/10-K/{CIK}/{acc}/{ticker}-{date}.htm, dei:EntityRegistrantName;
     only the first 400 KB of each file is read, where the cover page sits)

Usage (PG* env from the ftd-api unit, as scripts/sync_all_recent.sh does):
    python3 scripts/news_attribution_report.py [--sample NVDA]
"""
from __future__ import annotations

import argparse
import html
import logging
import os
import re
import sys
from collections import Counter, defaultdict

import psycopg2
from google.cloud import storage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_recent_relational import (  # noqa: E402
    RAW_BUCKET, _SEC_FILE_RE, article_mentions, load_company_names, normalize_company_name,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("news_attribution_report")

_REGISTRANT_RE = re.compile(r'name="dei:EntityRegistrantName"[^>]*>(.*?)</ix:nonNumeric>', re.S)


def registrant_names_from_10k(bucket: storage.Bucket) -> dict[str, str]:
    """Ticker -> official registrant name from its most recent 10-K in GCS."""
    latest: dict[str, str] = {}
    for blob in bucket.list_blobs(prefix="SEC/10-K/"):
        match = _SEC_FILE_RE.match(blob.name)
        if match:
            ticker = match.group(2).upper()
            if blob.name > latest.get(ticker, ""):
                latest[ticker] = blob.name
    names: dict[str, str] = {}
    for ticker, path in sorted(latest.items()):
        head = bucket.blob(path).download_as_bytes(start=0, end=400_000).decode("utf-8", errors="replace")
        found = _REGISTRANT_RE.search(head)
        if found:
            names[ticker] = html.unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip()
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sample", default="NVDA", help="ticker to print kept/dropped examples for")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "10.168.0.3"), port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "ftd_lakehouse_staging"), user=os.environ.get("PGUSER", "ftd_app"),
        password=os.environ["PGPASSWORD"],
    )
    conn.set_session(readonly=True)
    with conn.cursor() as cur:
        names_a = load_company_names(cur)

    filings = registrant_names_from_10k(storage.Client().bucket(RAW_BUCKET))
    names_b = {t: list(v) for t, v in names_a.items()}
    for ticker, official in filings.items():
        normalized = normalize_company_name(official)
        if normalized and normalized not in names_b.get(ticker, []):
            names_b.setdefault(ticker, []).append(normalized)
    logger.info("names: A=%d tickers, 10-K registrant names found=%d, B=%d tickers", len(names_a), len(filings), len(names_b))

    rules = {"A": Counter(), "B": Counter()}
    kept_tickers = {"A": set(), "B": set()}
    all_tickers: set[str] = set()
    samples: dict[str, list[str]] = defaultdict(list)
    total = 0
    with conn.cursor(name="news_scan") as cur:  # server-side cursor: streams rows
        cur.itersize = 5000
        cur.execute("SELECT target_ticker, content_body FROM staging_gnews")
        for ticker, body in cur:
            total += 1
            all_tickers.add(ticker)
            for scenario, names in (("A", names_a), ("B", names_b)):
                rule = article_mentions(body or "", ticker, names.get(ticker, []))
                rules[scenario][rule or "dropped"] += 1
                if rule:
                    kept_tickers[scenario].add(ticker)
            if ticker == args.sample:
                rule_b = article_mentions(body or "", ticker, names_b.get(ticker, []))
                key = "kept" if rule_b else "dropped"
                if len(samples[key]) < 4:
                    samples[key].append(f"[{rule_b or '-'}] {(body or '')[:110]}")
    conn.close()

    print(f"\nstaging_gnews rows: {total:,}   tickers with news: {len(all_tickers)}")
    for scenario in ("A", "B"):
        c = rules[scenario]
        kept = total - c["dropped"]
        print(f"\nScenario {scenario}: keep {kept:,} ({kept / max(total, 1):.1%}), drop {c['dropped']:,}; "
              f"tickers left with any news: {len(kept_tickers[scenario])}")
        for rule in ("dollar", "exchange", "paren", "name"):
            print(f"   {rule:9s} {c[rule]:>8,}")
    print(f"\n{args.sample} name(s) in B: {names_b.get(args.sample)}")
    for key in ("kept", "dropped"):
        print(f"{args.sample} {key} examples:")
        for line in samples[key]:
            print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
