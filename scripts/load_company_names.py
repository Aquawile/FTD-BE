#!/usr/bin/env python3
"""Load company display names into ticker_company_names (insert-only).

Sources, in order:
  1. gs://raw-data-strg/SEC/config/company_names.json, built from each company's
     10-K dei:EntityRegistrantName by scripts/build_company_names.py (the same
     names the GNews search uses).
  2. For tracked tickers still without a name: SEC's public ticker list
     (https://www.sec.gov/files/company_tickers.json), with corporate suffixes
     ("Inc.", "Corp", "/DE/") removed to match the style of source 1. Names are tidied for display: no trailing
"&"/"AND"/state tags, and all-caps names get normal casing ("MICROSOFT" ->
"Microsoft", short acronyms such as "CME" stay upper).

Existing rows are never changed or deleted; a ticker gets a row the first time
it appears in the file. Run nightly by sync_all_recent.sh. Uses the PG* env.

Usage: python3 scripts/load_company_names.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re

import psycopg2
import requests
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NAMES_BUCKET = "raw-data-strg"
NAMES_OBJECT = "SEC/config/company_names.json"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "FinanceTrackerDashboard izzybutera11@gmail.com")
_LOWER_WORDS = {"AND", "OF", "THE", "FOR", "DE"}
_SUFFIX = re.compile(
    r"(?:[\s,]+(?:inc|incorporated|corp|corporation|co|company|ltd|limited|plc|n\.?v|s\.?a|l\.?p|llc)\.?)+\s*$",
    re.IGNORECASE,
)


def _case_word(word: str, first: bool, only_word: bool) -> str:
    letters = word.rstrip(".!,")
    if any(ch.isdigit() or ch == "&" for ch in word):
        return word                                   # PG&E, AT&T, L3HARRIS
    if word in _LOWER_WORDS and not first:
        return word.lower()
    if len(letters) <= 2 or (only_word and len(letters) <= 4) or (len(letters) == 3 and not any(v in letters for v in "AEIOUY")):
        return word                                   # US, J., CME (whole name), NVR, CMS, KKR
    return "-".join(part.capitalize() for part in word.split("-"))


def display_name(raw: str) -> str:
    """Tidy a 10-K registrant name for display under a ticker."""
    name = re.sub(r"\s+", " ", raw.replace("\xa0", " ")).strip()
    name = re.sub(r"\s*[\\/][A-Z]{2}[\\/]\s*$", "", name)        # US BANCORP \DE\
    while True:
        trimmed = re.sub(r"(?:\s*,\s*[A-Za-z]|\s+(?:&|and|AND)|\s*,)\s*$", "", name).strip()
        if trimmed == name:
            break
        name = trimmed                                         # "JPMorgan Chase &", "SERVICENOW, I"
    if name.upper() == name and any(ch.isalpha() for ch in name):
        words = name.split(" ")
        name = " ".join(_case_word(w, i == 0, len(words) == 1) for i, w in enumerate(words))
    return name


def strip_corporate_suffix(name: str) -> str:
    """'AMPHENOL CORP /DE/' -> 'AMPHENOL', 'Blackstone Inc.' -> 'Blackstone'."""
    name = re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip()
    name = re.sub(r"\s*[\\/][A-Z]{2}[\\/]?\s*$", "", name)      # /DE/, \DE\, /MN
    stripped = _SUFFIX.sub("", name).strip(" ,")
    # Keep the suffix when stripping would leave one short word ("NEWS CORP", "Fox Corp").
    if not stripped or (" " not in stripped and len(stripped) <= 4):
        return name
    return stripped


def sec_names(symbols: set[str]) -> dict[str, str]:
    """Display names for symbols from SEC's public ticker list (one request)."""
    if not symbols:
        return {}
    resp = requests.get(SEC_TICKERS_URL, headers={"User-Agent": SEC_USER_AGENT}, timeout=30)
    resp.raise_for_status()
    titles = {row["ticker"].upper(): row["title"] for row in resp.json().values()}
    return {sym: display_name(strip_corporate_suffix(titles[sym])) for sym in symbols if titles.get(sym)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = json.loads(storage.Client().bucket(NAMES_BUCKET).blob(NAMES_OBJECT).download_as_text())
    names = {sym.upper(): display_name(raw) for sym, raw in payload.get("names", {}).items() if raw and raw.strip()}
    source = f"gs://{NAMES_BUCKET}/{NAMES_OBJECT} ({payload.get('generated_at', 'unknown')})"
    logger.info("company names: %d in %s", len(names), source)
    with psycopg2.connect("") as conn, conn.cursor() as cur:
        cur.execute("SELECT symbol FROM ticker_company_names")
        have = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT symbol FROM tickers WHERE name = symbol OR name IS NULL OR name = ''")
        unnamed = {r[0].upper() for r in cur.fetchall()} - have - set(names)
        fallback = sec_names(unnamed)
        logger.info("company names: %d tracked tickers not in the 10-K file; %d found in SEC's ticker list (%s)",
                    len(unnamed), len(fallback), ", ".join(sorted(unnamed - set(fallback))) or "all found")

        rows = [(sym, name, source) for sym, name in names.items()]
        rows += [(sym, name, SEC_TICKERS_URL) for sym, name in fallback.items()]
        if args.dry_run:
            for sym, name, _ in rows:
                if sym not in have:
                    print(f"{sym:<6} {name}")
            return 0

        inserted = 0
        for row in rows:
            cur.execute(
                "INSERT INTO ticker_company_names (symbol, company_name, source) VALUES (%s, %s, %s) "
                "ON CONFLICT (symbol) DO NOTHING",
                row,
            )
            inserted += cur.rowcount
        conn.commit()
    logger.info("company names: inserted %d new (%d already present)", inserted, len(rows) - inserted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
