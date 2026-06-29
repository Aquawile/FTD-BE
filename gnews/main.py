"""GCP Cloud Function — ingests GNews API articles into GCS.

Fetches financial news for Fortune 500 tickers using GNews Search API.
Stores raw API responses as gnews/YYYY-MM-DD/batch_XXX.json in GCS.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any

from flask import Request, jsonify
from google.cloud import storage
from google.api_core import retry
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GCS_BUCKET = os.environ.get('GCS_BUCKET', 'raw-data-strg')
GCS_PREFIX = os.environ.get('GCS_PREFIX', 'gnews')
GNEWS_API_KEY_SECRET = os.environ.get('GNEWS_API_KEY_SECRET', 'gnews-api-key')
GNEWS_API_URL = 'https://gnews.io/api/v4/search'
TICKERS_GCS_PATH = os.environ.get('TICKERS_GCS_PATH', 'SEC/config/fortune500.json')
BATCH_SIZE = 5
MAX_ARTICLES_PER_REQUEST = 10
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

# ---------------------------------------------------------------------------
# Clients (reused across warm invocations)
# ---------------------------------------------------------------------------

_storage_client: storage.Client | None = None
_secret_manager_client: Any | None = None  # google.cloud.secretmanager_v1


def _get_storage_bucket() -> storage.Bucket:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client.bucket(GCS_BUCKET)


def _get_secret_manager():
    try:
        from google.cloud import secretmanager_v1
        global _secret_manager_client
        if _secret_manager_client is None:
            _secret_manager_client = secretmanager_v1.SecretManagerServiceClient()
        return _secret_manager_client
    except ImportError:
        logger.warning("google-cloud-secret-manager not installed — falling back to env var")
        return None


def _get_api_key() -> str:
    """Retrieve GNews API key from environment (injected by --set-secrets or plain env var)."""
    # --set-secrets makes the secret value available as this env var
    secret_key = os.environ.get('GNEWS_API_KEY_SECRET', '')
    if secret_key:
        return secret_key

    # Fallback to plain env var
    env_key = os.environ.get('GNEWS_API_KEY', '')
    if env_key:
        return env_key

    raise RuntimeError(
        "GNews API key not found. Ensure the Cloud Function has "
        "--set-secrets=GNEWS_API_KEY_SECRET=<secret-name> configured, "
        "or provide GNEWS_API_KEY env var."
    )


# ---------------------------------------------------------------------------
# Ticker loading
# ---------------------------------------------------------------------------

def _load_tickers_from_gcs(bucket: storage.Bucket) -> list[str]:
    """Load Fortune 500 tickers from GCS config file."""
    blob_path = TICKERS_GCS_PATH.strip()
    if blob_path.startswith('gs://'):
        blob_path = blob_path.split('/', 3)[-1]

    blob = bucket.blob(blob_path)
    try:
        content = blob.download_as_text()
    except Exception as exc:
        logger.error("Failed to download ticker list from %s: %s", blob_path, exc)
        raise RuntimeError(f"Cannot load tickers from GCS: {exc}")

    payload = json.loads(content)
    if isinstance(payload, dict) and 'tickers' in payload:
        tickers = payload['tickers']
    elif isinstance(payload, list):
        tickers = payload
    else:
        raise ValueError(f"Unexpected ticker JSON shape: {type(payload)}")

    result = []
    seen: set[str] = set()
    for raw in tickers:
        ticker = str(raw).strip().upper().replace('.', '-')
        if ticker not in seen:
            seen.add(ticker)
            result.append(ticker)

    return result


# ---------------------------------------------------------------------------
# GNews API
# ---------------------------------------------------------------------------

def _is_retryable_error(exc: BaseException) -> bool:
    """Only retry on rate limit (429) and server errors (5xx)."""
    if not isinstance(exc, urllib.error.HTTPError):
        return True
    return exc.code == 429 or exc.code >= 500


@retry.Retry(
    predicate=_is_retryable_error,
    initial=RETRY_DELAY_SECONDS,
    maximum=RETRY_DELAY_SECONDS * 8,
    multiplier=2,
    deadline=60,
)
def _fetch_gnews_batch(api_key: str, query: str) -> dict[str, Any]:
    """Fetch articles from GNews API with exponential backoff on 429."""
    params = urllib.parse.urlencode({
        'q': query,
        'lang': 'en',
        'max': str(MAX_ARTICLES_PER_REQUEST),
        'sortby': 'publishedAt',
    })

    url = f"{GNEWS_API_URL}?{params}&apikey={api_key}"
    req = urllib.request.Request(url, headers={'User-Agent': 'FTD-GNews-Ingestion/1.0'})

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            logger.warning("Rate limited by GNews, backing off...")
            raise
        logger.error("GNews API error %d: %s", exc.code, exc.reason)
        raise


# ---------------------------------------------------------------------------
# GCS storage
# ---------------------------------------------------------------------------

def _write_batch_to_gcs(
    bucket: storage.Bucket,
    date_str: str,
    batch_num: int,
    query: str,
    payload: dict[str, Any],
) -> str:
    """Write a batch response to GCS and return the path."""
    filename = f"batch_{batch_num:03d}.json"
    gcs_path = f"{GCS_PREFIX}/{date_str}/{filename}"

    enriched = {
        'batch_number': batch_num,
        'query': query,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'article_count': len(payload.get('articles', [])),
        'total_articles_available': payload.get('totalArticles', 0),
        'data': payload,
    }

    blob = bucket.blob(gcs_path)
    blob.upload_from_string(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        content_type='application/json',
    )

    logger.info("Wrote batch %d to gs://%s/%s (%d articles)",
                batch_num, GCS_BUCKET, gcs_path, enriched['article_count'])

    return gcs_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def gnews_ingest(request: Request):
    """HTTP entry point for GNews ingestion.

    Triggered by Cloud Scheduler (recommended) or manual HTTP call.
    """

    # Handle CORS preflight for manual browser testing
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600',
        }
        return ('', 204, headers)

    if request.method != 'POST':
        return jsonify({'error': 'Method Not Allowed', 'allowed': ['POST']}), 405

    # ------------------------------------------------------------------
    # Note: Cloud Function is deployed with --allow-unauthenticated.
    # Cloud Scheduler will trigger this endpoint directly.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Load credentials and data
    # ------------------------------------------------------------------
    api_key = _get_api_key()
    bucket = _get_storage_bucket()

    try:
        tickers = _load_tickers_from_gcs(bucket)
    except Exception as exc:
        logger.error("Failed to load tickers: %s", exc)
        return jsonify({'error': f'Failed to load tickers: {exc}'}), 500

    if not tickers:
        return jsonify({'error': 'No tickers loaded'}), 500

    # ------------------------------------------------------------------
    # Batch and fetch
    # ------------------------------------------------------------------
    batches: list[dict[str, Any]] = []
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        query = ' OR '.join(f'"${ticker}"' for ticker in batch)
        batches.append({'tickers': batch, 'query': query})

    logger.info("Starting ingestion: %d tickers in %d batches", len(tickers), len(batches))

    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    uploaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for batch_num, batch_info in enumerate(batches, start=1):
        query = batch_info['query']
        batch_tickers = batch_info['tickers']

        try:
            payload = _fetch_gnews_batch(api_key, query)
            gcs_path = _write_batch_to_gcs(bucket, date_str, batch_num, query, payload)
            uploaded.append({
                'batch': batch_num,
                'path': gcs_path,
                'tickers': batch_tickers,
                'articles': len(payload.get('articles', [])),
            })

            # Small delay between requests to be respectful of API
            import time
            time.sleep(0.5)

        except urllib.error.HTTPError as exc:
            logger.error("Batch %d failed after retries: HTTP %d", batch_num, exc.code)
            failed.append({'batch': batch_num, 'tickers': batch_tickers, 'error': str(exc)})
        except Exception as exc:
            logger.error("Batch %d failed: %s", batch_num, exc)
            failed.append({'batch': batch_num, 'tickers': batch_tickers, 'error': str(exc)})

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------
    response = {
        'status': 'complete',
        'date': date_str,
        'total_batches': len(batches),
        'uploaded': len(uploaded),
        'failed': len(failed),
        'total_articles': sum(b['articles'] for b in uploaded),
        'files': uploaded,
    }
    if failed:
        response['failures'] = failed

    status_code = 207 if failed else 200
    return jsonify(response), status_code
