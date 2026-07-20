"""PostgreSQL connection pool and query utilities."""

from __future__ import annotations

import os
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

_POOL: psycopg2.pool.SimpleConnectionPool | None = None


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

    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _POOL
    if _POOL is None:
        dsn = _get_dsn()
        _POOL = psycopg2.pool.SimpleConnectionPool(minconn=1, maxconn=5, dsn=dsn)
    return _POOL


@contextmanager
def get_connection():
    """Yield a single PostgreSQL connection from the pool."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def query(sql: str, params: Sequence[Any] | None = None) -> list[tuple]:
    """Execute a parameterized SELECT query and return raw rows."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def query_dict(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT query and return rows as dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
