#!/usr/bin/env python3
"""Sync the most recent raw GCS data into the relational PostgreSQL tables.

Sources (gs://raw-data-strg):
  prices/{YYYY-MM-DD}/data.jsonl     -> staging_finnhub (one row per ticker per trading day)
  gnews/{YYYY-MM-DD}/batch_NNN.json  -> staging_gnews   (one row per article per queried ticker)

Then refreshes the price snapshot columns on ``tickers`` (current_price,
change_percent, price_as_of) from the latest staging_finnhub row per symbol.

Incremental and idempotent: only date folders on/after the newest date already
in PostgreSQL (minus a small lookback) are read. Prices are upserted on
(target_ticker, normalized_calendar_date); news rows are skipped when the same
(target_ticker, url, normalized_calendar_date) already exists.

Self-contained (no lakehouse/ or sec/ imports) so it can run from cron on the
staging API VM. Uses the standard PG* environment variables.

Usage:
    python3 scripts/sync_recent_relational.py [--lookback-days 3] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sync_recent_relational")

RAW_BUCKET = os.environ.get("RAW_DATA_BUCKET", "raw-data-strg")
_NUMERIC_FIELDS = ("current", "change", "percent_change", "high", "low", "open", "previous_close")


def _connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "10.168.0.3"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "ftd_lakehouse_staging"),
        user=os.environ.get("PGUSER", "ftd_app"),
        password=os.environ["PGPASSWORD"],
    )


def _list_date_folders(bucket: storage.Bucket, prefix: str, since: date) -> list[str]:
    """Return YYYY-MM-DD folder names under ``prefix`` that are >= ``since``."""
    folders = set()
    for blob in bucket.list_blobs(prefix=f"{prefix}/"):
        parts = blob.name.split("/")
        if len(parts) >= 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[1]):
            if date.fromisoformat(parts[1]) >= since:
                folders.add(parts[1])
    return sorted(folders)


_SEC_FILE_RE = re.compile(r"^SEC/(?:8-K|10-K)/(\d{10})/[^/]+/([a-z][a-z0-9_]*)-\d{8}\.html?$", re.IGNORECASE)


def load_gcs_ticker_cik_map(bucket: storage.Bucket) -> dict[str, str]:
    """Ticker -> CIK from SEC filings in GCS (SEC/{form}/{CIK}/{accession}/{ticker}-{date}.htm).

    The filing path's CIK folder is authoritative. The CIKs already stored in
    staging_finnhub / staging_gnews are NOT used: the old lakehouse loader
    shifted them (CLAUDE.md known issue #9). Tickers seen under more than one
    CIK, or with no ticker-named filing, are left out (stored as NULL).
    """
    seen: dict[str, set[str]] = {}
    for blob in bucket.list_blobs(prefix="SEC/"):
        match = _SEC_FILE_RE.match(blob.name)
        if match:
            seen.setdefault(match.group(2).upper(), set()).add(match.group(1))
    return {ticker: next(iter(ciks)) for ticker, ciks in seen.items() if len(ciks) == 1}


def _load_tracked_symbols(cur) -> set[str]:
    cur.execute("SELECT symbol FROM tickers")
    return {r[0].upper() for r in cur.fetchall()}


# ─── Prices ──────────────────────────────────────────────────────────────────

def sync_prices(conn, bucket, symbols, cik_map, lookback_days: int, dry_run: bool,
                since_override: date | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(normalized_calendar_date)::date FROM staging_finnhub")
        latest = cur.fetchone()[0] or date(2000, 1, 1)
    since = since_override or (latest - timedelta(days=lookback_days))
    folders = _list_date_folders(bucket, "prices", since)
    logger.info("prices: latest in PG=%s, reading %d GCS folder(s) since %s", latest, len(folders), since)

    # Weekend/holiday files repeat the last trading day's quote; key by the
    # quote's own timestamp date and keep the most recently written file.
    rows: dict[tuple[str, date], dict] = {}
    for folder in folders:
        blob = bucket.blob(f"prices/{folder}/data.jsonl")
        if not blob.exists():
            continue
        for line in blob.download_as_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            symbol = (rec.get("symbol") or "").upper()
            if symbol not in symbols or rec.get("current") is None or not rec.get("timestamp"):
                continue
            ts = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
            cal_date = ts.date()
            rows[(symbol, cal_date)] = {
                "target_ticker": symbol,
                "target_cik": cik_map.get(symbol),
                "symbol": symbol,
                "timestamp": ts.replace(tzinfo=None),
                "normalized_calendar_date": cal_date,
                **{k: rec.get(k) for k in _NUMERIC_FIELDS},
            }

    if dry_run:
        logger.info("prices: would upsert %d rows", len(rows))
        return len(rows)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with conn.cursor() as cur:
        for r in rows.values():
            cur.execute(
                "DELETE FROM staging_finnhub WHERE target_ticker = %s AND normalized_calendar_date = %s",
                (r["target_ticker"], r["normalized_calendar_date"]),
            )
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO staging_finnhub
                (target_ticker, target_cik, element_type, content_body, normalized_calendar_date,
                 ingest_date, symbol, "timestamp", "current", change, percent_change, high, low,
                 open, previous_close)
            VALUES %s
            """,
            [
                (
                    r["target_ticker"], r["target_cik"], "quantitative", "", r["normalized_calendar_date"],
                    now, r["symbol"], r["timestamp"], r["current"], r["change"], r["percent_change"],
                    r["high"], r["low"], r["open"], r["previous_close"],
                )
                for r in rows.values()
            ],
            page_size=1000,
        )
    conn.commit()
    logger.info("prices: upserted %d rows", len(rows))
    return len(rows)


# ─── News ────────────────────────────────────────────────────────────────────

def _normalize_text(value) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value))
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace").strip()


# ─── Attribution ─────────────────────────────────────────────────────────────
# A GNews batch queries ~5 tickers at once ("$MMM" OR "$AOS" ...) and the API
# matches loosely, so an article in a batch is not necessarily about every
# ticker in its query. In strict mode an article is kept for a ticker only if
# it actually mentions it.

_EXCHANGES = r"(?:NYSE(?:\s+American)?|NASDAQ|Nasdaq|AMEX|Cboe)"
_NAME_SUFFIX_RE = re.compile(
    r"[,\s]+(?:inc|incorporated|corp|corporation|co|company|ltd|limited|plc|n\.?v|s\.?a|ag|holdings?|group|the)\.?$",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str | None:
    """'NVIDIA CORP' -> 'NVIDIA', 'Apple Inc.' -> 'Apple'; None if too short to match safely."""
    base = re.sub(r"^the\s+", "", (name or "").strip(), flags=re.IGNORECASE)
    for _ in range(4):
        # SEC conformed names carry state tags and slashes: "NORTHROP GRUMMAN CORP /DE/", "WALT DISNEY CO/"
        stripped = re.sub(r"\s*/\s*[A-Z]{2,4}\s*/?\s*$|/+\s*$", "", base)
        stripped = _NAME_SUFFIX_RE.sub("", stripped).strip(" ,./")
        if stripped == base:
            break
        base = stripped
    # Short names only when they can't be an ordinary word ("3M" yes, "Co" no).
    return base if len(base) >= 3 or (len(base) >= 2 and any(c.isdigit() for c in base)) else None


def article_mentions(text: str, ticker: str, names: list[str]) -> str | None:
    """Which rule ties the article to the ticker: 'dollar', 'exchange', 'paren', 'name', or None.

    A bare upper-case ticker is not enough: tickers collide with acronyms and
    product names (e.g. "Step AOS" in a phone review was filed under AOS).
    """
    t = re.escape(ticker)
    if re.search(rf"\${t}\b", text, re.IGNORECASE):
        return "dollar"
    if re.search(rf"{_EXCHANGES}\s*:\s*{t}\b", text):
        return "exchange"
    if re.search(rf"\(\s*{t}\s*\)", text):  # "Apple (AAPL)"
        return "paren"
    for name in names:
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text, re.IGNORECASE):
            return "name"
    return None


def load_company_names(cur) -> dict[str, list[str]]:
    """Ticker -> match names from tickers.name (only where it isn't just the symbol)."""
    cur.execute("SELECT symbol, name FROM tickers WHERE name IS NOT NULL AND name <> symbol")
    names: dict[str, list[str]] = {}
    for symbol, name in cur.fetchall():
        normalized = normalize_company_name(name)
        if normalized:
            names.setdefault(symbol.upper(), []).append(normalized)
    return names


def batch_tickers(payload: dict, symbols: set[str]) -> list[str]:
    """Tracked tickers a GNews batch file was fetched for.

    Files written since the name-based queries list them in "tickers"; older
    files only have "$TICK" terms in the query string.
    """
    raw = payload.get("tickers") or re.findall(r"\$([A-Z]{1,5})", payload.get("query", ""))
    return [str(t).upper() for t in raw if str(t).upper() in symbols]


def sync_news(conn, bucket, symbols, cik_map, lookback_days: int, dry_run: bool,
              since_override: date | None = None, strict: bool = False,
              names: dict[str, list[str]] | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(ingest_date)::date FROM staging_gnews")
        latest = cur.fetchone()[0] or date(2000, 1, 1)
        # Every existing (ticker, url-or-body, date) key, so re-reading folders never duplicates.
        cur.execute("SELECT target_ticker, COALESCE(url, LEFT(content_body, 200)), normalized_calendar_date::date FROM staging_gnews")
        existing = set(cur.fetchall())
    since = since_override or (latest - timedelta(days=lookback_days))
    folders = _list_date_folders(bucket, "gnews", since)
    logger.info("gnews: latest ingest in PG=%s, reading %d GCS folder(s) since %s%s",
                latest, len(folders), since, " (strict attribution)" if strict else "")

    inserted = skipped_existing = skipped_unrelated = 0
    # One day-folder at a time: bounded memory for long backfills, committed as it goes.
    for folder in folders:
        rows: dict[tuple[str, str, date], tuple] = {}
        for blob in bucket.list_blobs(prefix=f"gnews/{folder}/"):
            if not blob.name.endswith(".json"):
                continue
            try:
                payload = json.loads(blob.download_as_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("gnews: failed to parse %s: %s", blob.name, exc)
                continue
            tickers = batch_tickers(payload, symbols)
            if not tickers:
                continue
            fetched_at = payload.get("fetched_at")
            ingest_date = datetime.fromisoformat(fetched_at).date() if fetched_at else date.fromisoformat(folder)
            for article in payload.get("data", {}).get("articles", []):
                parts = [_normalize_text(article.get(k)) for k in ("title", "description", "content")]
                content_body = ". ".join(p for p in parts if p)
                if len(content_body) < 50 or not article.get("publishedAt"):
                    continue
                published = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")).date()
                url = article.get("url") or None
                for ticker in tickers:
                    if strict and not article_mentions(content_body, ticker, (names or {}).get(ticker, [])):
                        skipped_unrelated += 1
                        continue
                    rows[(ticker, url or content_body[:200], published)] = (
                        ticker, cik_map.get(ticker), "narrative", content_body, published, ingest_date, url,
                    )

        new_keys = [k for k in rows if k not in existing]
        skipped_existing += len(rows) - len(new_keys)
        if new_keys and not dry_run:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO staging_gnews
                        (target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, url)
                    VALUES %s
                    """,
                    [rows[k] for k in new_keys],
                    page_size=1000,
                )
            conn.commit()
        existing.update(new_keys)
        inserted += len(new_keys)

    verb = "would insert" if dry_run else "inserted"
    logger.info("gnews: %s %d new rows (%d already present, %d skipped as unrelated)",
                verb, inserted, skipped_existing, skipped_unrelated)
    return inserted


# ─── Tickers snapshot ────────────────────────────────────────────────────────

def refresh_ticker_prices(conn, dry_run: bool) -> int:
    sql = """
        WITH latest AS (
            SELECT DISTINCT ON (target_ticker)
                target_ticker, "current", percent_change,
                COALESCE("timestamp", normalized_calendar_date) AS as_of
            FROM staging_finnhub
            WHERE "current" IS NOT NULL
            ORDER BY target_ticker, normalized_calendar_date DESC, ingest_date DESC NULLS LAST
        )
        UPDATE tickers t
        SET current_price = l."current",
            change_percent = l.percent_change,
            price_as_of = l.as_of
        FROM latest l
        WHERE l.target_ticker = t.symbol
          AND (t.price_as_of IS NULL OR l.as_of > t.price_as_of)
    """
    if dry_run:
        return 0
    with conn.cursor() as cur:
        cur.execute(sql)
        updated = cur.rowcount
    conn.commit()
    logger.info("tickers: refreshed price snapshot for %d symbols", updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--lookback-days", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", type=date.fromisoformat, help="backfill from this date (YYYY-MM-DD) instead of the lookback")
    parser.add_argument("--skip-prices", action="store_true", help="only sync news")
    parser.add_argument("--strict-attribution", action="store_true",
                        help="keep an article for a ticker only if it mentions it (see article_mentions)")
    args = parser.parse_args()

    bucket = storage.Client().bucket(RAW_BUCKET)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            symbols = _load_tracked_symbols(cur)
        cik_map = load_gcs_ticker_cik_map(bucket)
        logger.info("Loaded %d tracked symbols; %d have a CIK from GCS filings", len(symbols), len(symbols & cik_map.keys()))
        if not args.skip_prices:
            sync_prices(conn, bucket, symbols, cik_map, args.lookback_days, args.dry_run, args.since)
        names = None
        if args.strict_attribution:
            with conn.cursor() as cur:
                names = load_company_names(cur)
        sync_news(conn, bucket, symbols, cik_map, args.lookback_days, args.dry_run,
                  since_override=args.since, strict=args.strict_attribution, names=names)
        refresh_ticker_prices(conn, args.dry_run)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
