"""PostgreSQL connection pool and query utilities."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Sequence

import psycopg2
import psycopg2.pool
import psycopg2.extras

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# One pool for the whole API process.
#   * ThreadedConnectionPool: the API runs route handlers in a thread pool, so the pool must be thread-safe.
#   * A semaphore of the same size makes a request WAIT for a free connection (up to _WAIT_SECONDS) instead of
#     failing at once with "connection pool exhausted". A page load fires ~7 requests together, so more than a
#     handful of simultaneous requests is normal, not an error.
#   * Postgres allows 100 connections; the API holds at most _POOL_MAX, leaving room for cron scripts and admin use.
_POOL: psycopg2.pool.ThreadedConnectionPool | None = None
_POOL_LOCK = threading.Lock()
_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "20"))
_POOL_MIN = int(os.environ.get("DB_POOL_MIN", "5"))
_WAIT_SECONDS = float(os.environ.get("DB_POOL_WAIT_SECONDS", "15"))
_SLOTS = threading.BoundedSemaphore(_POOL_MAX)


class PoolTimeout(Exception):
    """No database connection became free in time (the server is overloaded). The API answers 503."""


def _get_dsn() -> str:
    host = os.environ.get("PGHOST", "")
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "")
    user = os.environ.get("PGUSER", "")
    password = os.environ.get("PGPASSWORD", "")

    missing = [name for name, val in [
        ("PGHOST", host),
        ("PGDATABASE", dbname),
        ("PGUSER", user),
        ("PGPASSWORD", password),
    ] if not val]

    if missing:
        raise EnvironmentError(
            f"Missing required PostgreSQL environment variables: {', '.join(missing)}"
        )

    # connect_timeout: never hang forever on a dead server. keepalives: notice a silently dropped connection.
    return (f"host={host} port={port} dbname={dbname} user={user} password={password} "
            "connect_timeout=10 keepalives=1 keepalives_idle=30 keepalives_interval=10 keepalives_count=3")


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                _POOL = psycopg2.pool.ThreadedConnectionPool(minconn=_POOL_MIN, maxconn=_POOL_MAX, dsn=_get_dsn())
    return _POOL


def _alive(conn) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.rollback()
        return True
    except Exception:
        return False


@contextmanager
def get_connection(validate: bool = False):
    """Yield a pooled PostgreSQL connection, waiting for a free one if all are busy.

    validate=True first checks the connection still works (used before writes, which must not be retried
    half-way) and swaps a dead one for a fresh one.
    """
    if not _SLOTS.acquire(timeout=_WAIT_SECONDS):
        raise PoolTimeout(f"no database connection became free within {_WAIT_SECONDS:g}s")
    try:
        pool = _get_pool()
        conn = pool.getconn()
        if validate:
            for _ in range(3):
                if _alive(conn):
                    break
                pool.putconn(conn, close=True)   # dead (database restarted, idle drop): discard it
                conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)                   # the pool rolls back an unfinished transaction before reuse
    finally:
        _SLOTS.release()


def _read(run):
    """Run a read-only query; if the pooled connection turned out to be dead, retry once on a fresh one."""
    try:
        return run()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return run()


def query(sql: str, params: Sequence[Any] | None = None) -> list[tuple]:
    """Execute a parameterized SELECT query and return raw rows."""
    def run():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
    return _read(run)


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    """Execute a parameterized statement that does not return rows."""
    with get_connection(validate=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def query_dict(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT query and return rows as dicts."""
    def run():
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
    return _read(run)
