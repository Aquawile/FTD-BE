"""Pytest configuration and fixtures for test suite."""

import os
import pytest
import sys
from pathlib import Path

# Provide dummy PG env vars so app.db doesn't raise at import or call time.
# Unit tests mock at the route or service layer, so no real connection is needed.
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGDATABASE", "ftd_lakehouse_test")
os.environ.setdefault("PGUSER", "ftd_app")
os.environ.setdefault("PGPASSWORD", os.environ.get("PGPASSWORD", "temp_password_123"))

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.db import get_connection


# db_integration tests run against a throwaway Postgres built by
# tests/schema/setup_test_db.sh (in CI: a postgres:15 service container).
#
# REQUIRE_DB=1 (set in CI): the database must be reachable, and any
# db_integration test that skips counts as a failure, so they can never pass
# by silently not running. Without it (e.g. a laptop with no test database),
# db_integration tests are skipped and the reason is printed.
_REQUIRE_DB = os.environ.get("REQUIRE_DB") == "1"
_PROTECTED_DATABASES = {"ftd_lakehouse_staging"}
_DB_READY: bool = False
_DB_REASON: str = ""


def _check_database() -> tuple[bool, str]:
    dbname = os.environ.get("PGDATABASE", "")
    if dbname in _PROTECTED_DATABASES:
        return False, f"PGDATABASE={dbname} is a real database; db_integration tests create and delete rows"
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.users'), to_regclass('public.tickers')")
                users, tickers = cur.fetchone()
            conn.rollback()
        if users is None or tickers is None:
            return False, f"{dbname} has no schema; build it with tests/schema/setup_test_db.sh"
        return True, ""
    except Exception as exc:  # noqa: BLE001 - any connection problem means "not available"
        return False, f"cannot connect to {os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{dbname}: {exc}"


def pytest_collection_modifyitems(config, items):
    """Run db_integration tests only against a reachable throwaway database."""
    global _DB_READY, _DB_REASON
    if not any("db_integration" in item.keywords for item in items):
        return
    _DB_READY, _DB_REASON = _check_database()
    if _DB_READY:
        return
    if _REQUIRE_DB:
        raise pytest.UsageError(f"REQUIRE_DB=1 but the test database is unavailable: {_DB_REASON}")
    skip_db = pytest.mark.skip(reason=f"Database unavailable: {_DB_REASON}")
    for item in items:
        if "db_integration" in item.keywords:
            item.add_marker(skip_db)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """With REQUIRE_DB=1, a skipped db_integration test is a failure (missing seed data, etc.)."""
    outcome = yield
    report = outcome.get_result()
    if _REQUIRE_DB and report.skipped and "db_integration" in item.keywords and not hasattr(report, "wasxfail"):
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        report.outcome = "failed"
        report.longrepr = f"db_integration test skipped under REQUIRE_DB=1: {reason}"


@pytest.fixture
def db_transaction():
    """Function-scoped fixture that wraps each test in a transaction and rolls back.
    
    Usage:
        def test_something(db_transaction):
            # Test runs inside a transaction
            # All changes automatically rolled back after test
            pass
    
    This fixture:
    1. Begins a transaction with autocommit=False
    2. Yields the connection to the test
    3. Rolls back the transaction after test completes (regardless of pass/fail)
    4. Restores autocommit=True
    
    Usage is optional - only tests that need transaction isolation should request this fixture.
    Tests marked with @pytest.mark.db_integration that don't use this fixture
    are responsible for their own cleanup (e.g., using addCleanup).
    """
    with get_connection() as conn:
        conn.autocommit = False
        try:
            yield conn
        finally:
            conn.rollback()
            conn.autocommit = True


@pytest.fixture
def db_connection():
    """Function-scoped fixture providing a database connection with autocommit=True.
    
    Use this for tests that need direct database access but don't need
    transaction rollback (tests handle their own cleanup via addCleanup).
    """
    with get_connection() as conn:
        conn.autocommit = True
        yield conn