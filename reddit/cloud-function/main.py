"""GCP Cloud Function — receives Reddit payloads from Devvit and writes to GCS.

Each post is written once per matched ticker under:
  reddit/{ticker}/YYYY-MM-DD/{post_id}.json
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from flask import Request, jsonify
from google.cloud import storage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get('INGESTION_API_KEY', '')
GCS_BUCKET = os.environ.get('GCS_BUCKET', 'raw-data-strg')
GCS_REDDIT_PREFIX = os.environ.get('GCS_REDDIT_PREFIX', 'reddit')
MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Clients (module-level so they are reused across invocations)
# ---------------------------------------------------------------------------

_storage_client: storage.Client | None = None


def _get_bucket() -> storage.Bucket:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client.bucket(GCS_BUCKET)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_THING_PREFIX_RE = re.compile(r'^t[13]_')
_SAFE_TICKER = re.compile(r'^[A-Z0-9][A-Z0-9.\-]{0,14}$')
_SAFE_POST_ID = re.compile(r'^[a-z0-9]+$')


def _sanitize_post_id(thing_id: str) -> str:
    return _THING_PREFIX_RE.sub('', thing_id)


def _utc_date_from_iso(iso_timestamp: str) -> str:
    dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d')


def _gcs_path(ticker: str, post_id: str, timestamp: str) -> str:
    date_str = _utc_date_from_iso(timestamp)
    return f"{GCS_REDDIT_PREFIX}/{ticker}/{date_str}/{post_id}.json"


def _validate_request(request: Request) -> tuple[bool, str]:
    provided = request.headers.get('X-API-Key', '')
    if not API_KEY:
        logger.warning("INGESTION_API_KEY is not configured — rejecting all requests")
        return False, 'Server misconfigured'
    if provided != API_KEY:
        logger.warning("Rejected request with bad API key from %s", request.remote_addr)
        return False, 'Invalid API key'
    return True, ''


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

def reddit_ingest(request: Request):
    """POST / — accept Reddit post batches from Devvit, persist to GCS."""

    if request.method != 'POST':
        return jsonify({'error': 'Method Not Allowed', 'allowed': ['POST']}), 405

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    ok, reason = _validate_request(request)
    if not ok:
        return jsonify({'error': 'Unauthorized', 'detail': reason}), 401

    # ------------------------------------------------------------------
    # Payload size guard
    # ------------------------------------------------------------------
    content_length = request.content_length or 0
    if content_length > MAX_PAYLOAD_BYTES:
        return jsonify({
            'error': 'Payload too large',
            'max_bytes': MAX_PAYLOAD_BYTES,
        }), 413

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------
    try:
        body = request.get_json(force=True)
    except Exception as exc:
        return jsonify({'error': f'Invalid JSON: {exc}'}), 400

    if not isinstance(body, dict) or 'posts' not in body:
        return jsonify({'error': 'Invalid payload: expected { posts: [...] }'}), 400

    posts = body['posts']
    if not isinstance(posts, list):
        return jsonify({'error': 'posts must be an array'}), 400

    if not posts:
        return jsonify({'status': 'ok', 'uploaded': 0}), 200

    # ------------------------------------------------------------------
    # Write each post to GCS under every matched ticker folder
    # ------------------------------------------------------------------
    bucket = _get_bucket()
    uploaded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for post in posts:
        if not isinstance(post, dict):
            skipped.append({'reason': 'not-a-dict', 'item': str(post)})
            continue

        raw_id = str(post.get('id', '')).strip()
        if not raw_id:
            skipped.append({'reason': 'missing-id', 'item': post})
            continue

        post_id = _sanitize_post_id(raw_id)
        if not _SAFE_POST_ID.match(post_id):
            skipped.append({'reason': 'suspicious-post-id', 'id': raw_id})
            continue

        timestamp = str(post.get('timestamp', '')).strip()
        if not timestamp:
            skipped.append({'reason': 'missing-timestamp', 'id': raw_id})
            continue

        tickers = post.get('tickers')
        if not isinstance(tickers, list) or not tickers:
            skipped.append({'reason': 'missing-tickers', 'id': raw_id})
            continue

        for ticker in tickers:
            ticker_str = str(ticker).strip().upper()
            if not _SAFE_TICKER.match(ticker_str):
                skipped.append({'reason': 'suspicious-ticker', 'id': raw_id, 'ticker': ticker_str})
                continue

            gcs_path = _gcs_path(ticker_str, post_id, timestamp)
            blob = bucket.blob(gcs_path)

            try:
                blob.upload_from_string(
                    json.dumps(post, ensure_ascii=False, indent=2),
                    content_type='application/json',
                )
                uploaded.append({'id': raw_id, 'ticker': ticker_str, 'path': gcs_path})
            except Exception as exc:
                logger.exception("Failed to write %s: %s", gcs_path, exc)
                skipped.append({'reason': f'gcs-write-failed: {exc}', 'id': raw_id, 'ticker': ticker_str})

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------
    status_code = 207 if skipped else 200
    response: dict[str, Any] = {
        'status': 'partial' if skipped else 'ok',
        'uploaded': len(uploaded),
        'skipped': len(skipped),
        'files': uploaded,
    }
    if skipped:
        response['failures'] = skipped

    return jsonify(response), status_code
