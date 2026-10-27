"""db_integration: the connection pool under load, and its recovery from failures, against a real Postgres.

The staging incident: a page load fires ~7 requests at once, the pool held 5 connections and raised
"connection pool exhausted", so a user got an HTTP 500. These tests pin the fix: requests wait for a free
connection, a truly overloaded server answers 503 (not 500), and bad connections never leak into later requests.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import httpx
import psycopg2
import pytest

from app import db

pytestmark = pytest.mark.db_integration


@pytest.fixture
def pool_of():
    """Swap the module pool for one of a given size; restore the original afterwards."""
    saved = (db._POOL, db._POOL_MAX, db._POOL_MIN, db._WAIT_SECONDS, db._SLOTS)

    def swap(size: int, wait: float = 15.0):
        if db._POOL is not None:
            db._POOL.closeall()
        db._POOL = None
        db._POOL_MAX, db._POOL_MIN, db._WAIT_SECONDS = size, min(saved[2], size), wait
        db._SLOTS = threading.BoundedSemaphore(size)

    yield swap
    if db._POOL is not None:
        db._POOL.closeall()
    db._POOL, db._POOL_MAX, db._POOL_MIN, db._WAIT_SECONDS, db._SLOTS = (None, *saved[1:])


def _terminate(pid: int) -> None:
    raw = psycopg2.connect(db._get_dsn())
    raw.autocommit = True
    with raw.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
    raw.close()


def test_a_burst_far_larger_than_the_pool_all_succeeds():
    n = 60
    gate = threading.Barrier(n)

    def one(_):
        gate.wait(10)                              # every request reaches the pool at the same instant
        return db.query("SELECT pg_sleep(0.3), 1")

    with ThreadPoolExecutor(n) as ex:
        rows = list(ex.map(one, range(n)))
    assert all(r[0][1] == 1 for r in rows)


def test_requests_wait_for_a_free_connection_instead_of_failing(pool_of):
    pool_of(2)
    started = time.time()
    with ThreadPoolExecutor(12) as ex:
        rows = list(ex.map(lambda _: db.query("SELECT pg_sleep(0.2), 1"), range(12)))
    assert all(r[0][1] == 1 for r in rows)
    assert time.time() - started >= 1.0   # 12 queries x 0.2 s on 2 connections: they queued, none failed


def test_a_truly_overloaded_server_times_out_with_a_clear_error(pool_of):
    pool_of(1, wait=0.3)
    held, release = threading.Event(), threading.Event()

    def hold():
        with db.get_connection():
            held.set()
            release.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    held.wait(5)
    try:
        started = time.time()
        with pytest.raises(db.PoolTimeout):
            db.query("SELECT 1")
        assert time.time() - started < 2
    finally:
        release.set()
        t.join()
    assert db.query("SELECT 1") == [(1,)]     # and it recovers once the connection is free


def test_a_failed_query_does_not_poison_the_next_request(pool_of):
    pool_of(1)                                  # one connection: the next request reuses the same one
    with pytest.raises(psycopg2.errors.DivisionByZero):
        db.query("SELECT 1/0")
    assert db.query("SELECT 1") == [(1,)]


def test_a_dead_connection_is_replaced_for_reads_and_for_writes(pool_of):
    pool_of(1)
    assert db.query("SELECT 1") == [(1,)]
    with db.get_connection() as c:
        pid = c.info.backend_pid
    _terminate(pid)                             # the database drops the idle connection (restart, idle timeout)
    assert db.query("SELECT 1") == [(1,)]       # a read retries once on a fresh connection
    with db.get_connection() as c:
        pid = c.info.backend_pid
    _terminate(pid)
    db.execute("SELECT 1")                      # a write checks the connection first, so it is never half-sent


def test_the_real_app_answers_a_burst_with_no_errors():
    from app.main import app

    identity = {"firebase_uid": f"pool-burst-{uuid4().hex}", "email": f"pool.burst.{uuid4().hex[:8]}@example.test", "email_verified": True}

    async def burst():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            auth = {"Authorization": "Bearer x"}
            await client.get("/users/me/permissions", headers=auth)     # first sign-in creates the user
            calls = []
            for i in range(90):
                path = ["/tickers/tracked?limit=3", "/dashboard/stats", "/health", "/users/me/permissions", "/alerts/summary", "/workspaces"][i % 6]
                calls.append(client.get(path, headers=auth))
            return await asyncio.gather(*calls)

    with patch("app.auth.middleware.validate_firebase_token_with_reason", return_value=(identity, None)):
        responses = asyncio.run(burst())
    codes = [r.status_code for r in responses]
    assert [c for c in codes if c != 200] == [], f"non-200 responses: {sorted(set(codes))}"
    with db.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = current_user")
        assert cur.fetchone()[0] <= db._POOL_MAX + 10   # bounded by the pool (a leak would show as ~90, one per request)
