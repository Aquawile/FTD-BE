#!/usr/bin/env python3
"""Load company display names into ticker_company_names (insert-only).

Source: gs://raw-data-strg/SEC/config/company_names.json, built from each
company's 10-K dei:EntityRegistrantName by scripts/build_company_names.py (the
same names the GNews search uses). Names are tidied for display: no trailing
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
import re

import psycopg2
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NAMES_BUCKET = "raw-data-strg"
NAMES_OBJECT = "SEC/config/company_names.json"
_LOWER_WORDS = {"AND", "OF", "THE", "FOR", "DE"}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = json.loads(storage.Client().bucket(NAMES_BUCKET).blob(NAMES_OBJECT).download_as_text())
    names = {sym.upper(): display_name(raw) for sym, raw in payload.get("names", {}).items() if raw and raw.strip()}
    source = f"gs://{NAMES_BUCKET}/{NAMES_OBJECT} ({payload.get('generated_at', 'unknown')})"
    logger.info("company names: %d in %s", len(names), source)
    if args.dry_run:
        for sym in sorted(names)[:25]:
            print(f"{sym:<6} {names[sym]}")
        return 0

    with psycopg2.connect("") as conn, conn.cursor() as cur:
        inserted = 0
        for sym, name in names.items():
            cur.execute(
                "INSERT INTO ticker_company_names (symbol, company_name, source) VALUES (%s, %s, %s) "
                "ON CONFLICT (symbol) DO NOTHING",
                (sym, name, source),
            )
            inserted += cur.rowcount
        conn.commit()
    logger.info("company names: inserted %d new (%d already present)", inserted, len(names) - inserted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
