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


def _load_ticker_maps(cur) -> tuple[set[str], dict[str, str]]:
    """Tracked symbols and symbol -> CIK (from rows that already carry a CIK)."""
    cur.execute("SELECT symbol FROM tickers")
    symbols = {r[0].upper() for r in cur.fetchall()}
    cur.execute(
        """
        SELECT target_ticker, MAX(target_cik)
        FROM (
            SELECT target_ticker, target_cik FROM staging_finnhub WHERE target_cik IS NOT NULL
            UNION ALL
            SELECT target_ticker, target_cik FROM staging_gnews WHERE target_cik IS NOT NULL
        ) s
        GROUP BY target_ticker
        """
    )
    cik_map = {r[0].upper(): r[1] for r in cur.fetchall()}
    return symbols, cik_map


# ─── Prices ──────────────────────────────────────────────────────────────────

def sync_prices(conn, bucket, symbols, cik_map, lookback_days: int, dry_run: bool) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(normalized_calendar_date)::date FROM staging_finnhub")
        latest = cur.fetchone()[0] or date(2000, 1, 1)
    since = latest - timedelta(days=lookback_days)
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


def sync_news(conn, bucket, symbols, cik_map, lookback_days: int, dry_run: bool) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(ingest_date)::date FROM staging_gnews")
        latest = cur.fetchone()[0] or date(2000, 1, 1)
    since = latest - timedelta(days=lookback_days)
    folders = _list_date_folders(bucket, "gnews", since)
    logger.info("gnews: latest ingest in PG=%s, reading %d GCS folder(s) since %s", latest, len(folders), since)

    # Same shaping as lakehouse/pipelines/gnews_normalizer.py
    rows: dict[tuple[str, str, date], tuple] = {}
    for folder in folders:
        for blob in bucket.list_blobs(prefix=f"gnews/{folder}/"):
            if not blob.name.endswith(".json"):
                continue
            try:
                payload = json.loads(blob.download_as_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("gnews: failed to parse %s: %s", blob.name, exc)
                continue
            tickers = [t for t in re.findall(r"\$([A-Z]{1,5})", payload.get("query", "")) if t in symbols]
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
                    rows[(ticker, url or content_body[:200], published)] = (
                        ticker, cik_map.get(ticker), "narrative", content_body, published, ingest_date, url,
                    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT target_ticker, COALESCE(url, LEFT(content_body, 200)), normalized_calendar_date::date "
            "FROM staging_gnews WHERE normalized_calendar_date >= %s",
            (min((k[2] for k in rows), default=since),),
        )
        existing = set(cur.fetchall())
    new_rows = [v for k, v in rows.items() if k not in existing]

    if dry_run:
        logger.info("gnews: would insert %d new rows (%d already present)", len(new_rows), len(rows) - len(new_rows))
        return len(new_rows)

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO staging_gnews
                (target_ticker, target_cik, element_type, content_body, normalized_calendar_date, ingest_date, url)
            VALUES %s
            """,
            new_rows,
            page_size=1000,
        )
    conn.commit()
    logger.info("gnews: inserted %d new rows (%d already present)", len(new_rows), len(rows) - len(new_rows))
    return len(new_rows)


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
    args = parser.parse_args()

    bucket = storage.Client().bucket(RAW_BUCKET)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            symbols, cik_map = _load_ticker_maps(cur)
        logger.info("Loaded %d tracked symbols, %d with CIKs", len(symbols), len(cik_map))
        sync_prices(conn, bucket, symbols, cik_map, args.lookback_days, args.dry_run)
        sync_news(conn, bucket, symbols, cik_map, args.lookback_days, args.dry_run)
        refresh_ticker_prices(conn, args.dry_run)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
