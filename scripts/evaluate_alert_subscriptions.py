#!/usr/bin/env python3
"""Evaluate alert subscriptions once (app/services/alert_evaluator.py).

Run at the end of each data sync by scripts/sync_all_recent.sh, after prices,
news and the vectorized mirror are up to date. Uses the PG* environment.

Usage:
    python3 scripts/evaluate_alert_subscriptions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# On the API VM this file lives in ~/app/scripts, next to the app package (~/app/app).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.alert_evaluator import evaluate_subscriptions  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="show what would fire without writing")
    args = parser.parse_args()
    for r in evaluate_subscriptions(dry_run=args.dry_run):
        print(f"sub {r['id']:>4} {r['ticker']:<6} {r['type']:<12} {r.get('label', r.get('status'))}"
              + (f"  -> ALERT: {r['message']}" if r.get("fired") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
