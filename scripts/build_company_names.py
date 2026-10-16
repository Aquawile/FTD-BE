#!/usr/bin/env python3
"""Write ticker -> company name for the GNews ingestion queries.

Source: the official registrant name (dei:EntityRegistrantName) on each
company's latest 10-K in gs://raw-data-strg/SEC/10-K/, normalized the way news
writes it ("NVIDIA CORP" -> "NVIDIA", "3M COMPANY" -> "3M"). Tickers without a
ticker-named 10-K are left out; the ingestion falls back to the ticker for them.

Output JSON (written locally; upload next to SEC/config/fortune500.json):
    {"source": "...", "generated_at": "...", "names": {"NVDA": "NVIDIA", ...}}

Usage:
    python3 scripts/build_company_names.py --out company_names.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from google.cloud import storage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_attribution_report import registrant_names_from_10k  # noqa: E402
from sync_recent_relational import RAW_BUCKET, normalize_company_name  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    official = registrant_names_from_10k(storage.Client().bucket(RAW_BUCKET))
    names = {t: n for t, n in ((t, normalize_company_name(o)) for t, o in official.items()) if n}
    payload = {
        "source": "dei:EntityRegistrantName from latest 10-K in gs://raw-data-strg/SEC/10-K/ (normalized)",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "names": dict(sorted(names.items())),
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"wrote {len(names)} names to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
