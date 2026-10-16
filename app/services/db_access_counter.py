"""Global counters for PostgreSQL access from non-user data paths.

After the Layer 8 migration, the SEC-data API endpoints read from
`ftd-vectorized-data` (GCS). The old PostgreSQL functions remain in
`app/crud.py` as fallbacks but should never be called for SEC data.

If a counter increments to > 0 after migration, the old PostgreSQL path
was hit and the migration is incomplete.
"""
import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

_counters: dict[str, int] = defaultdict(int)
_lock = threading.Lock()


def increment_counter(endpoint: str) -> None:
    """Increment the counter for an endpoint that should no longer use Postgres."""
    with _lock:
        _counters[endpoint] += 1
        if _counters[endpoint] == 1:
            logger.warning(
                "DB_ACCESS_COUNTER_HIT: endpoint=%s has been called %d times. "
                "This endpoint should use vectorized GCS data, not PostgreSQL.",
                endpoint, _counters[endpoint],
            )
        elif _counters[endpoint] <= 5:
            logger.warning(
                "DB_ACCESS_COUNTER_HIT: endpoint=%s call #%d — DB fallback active.",
                endpoint, _counters[endpoint],
            )


def get_counters() -> dict[str, int]:
    """Return a snapshot of all counters."""
    with _lock:
        return dict(_counters)


def reset_counters() -> None:
    """Reset all counters to zero (for testing)."""
    with _lock:
        _counters.clear()
