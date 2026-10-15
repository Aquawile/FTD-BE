"""Pytest configuration and fixtures for test suite."""

import os
import pytest
import subprocess
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


_DB_READY: bool = False


def _has_gcloud_auth() -> bool:
    """Check if gcloud has an active authenticated account."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _run_db_reset() -> bool:
    """Run the database reset script. Returns True if successful or skipped.

    Returns False (not True) when gcloud auth is missing so that
    db_integration tests can be explicitly skipped rather than running
    against unavailable infrastructure.
    """
    if not _has_gcloud_auth():
        print("WARNING: No active gcloud account. Database reset skipped.")
        return False

    try:
        result = subprocess.run(
            ["bash", "scripts/manage_test_databases.sh", "reset-test-dbs"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"WARNING: Database reset failed: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("WARNING: Database reset timed out")
        return False
    except Exception as e:
        print(f"WARNING: Database reset failed: {e}")
        return False


@pytest.fixture(scope="session", autouse=True)
def reset_test_databases():
    """Session-scoped fixture to reset test databases before and after test session.

    Runs `scripts/manage_test_databases.sh reset-test-dbs` before the test session
    to ensure clean state, and again after the session to leave databases clean.
    If the reset fails (e.g. no gcloud auth), only ``db_integration`` tests are
    skipped — unit tests continue to run.
    """
    global _DB_READY

    # Before session
    print("\n=== Resetting test databases (session start) ===")
    _DB_READY = _run_db_reset()

    yield

    # After session
    print("\n=== Resetting test databases (session end) ===")
    _run_db_reset()


def pytest_collection_modifyitems(config, items):
    """Skip db_integration tests when the database is unavailable."""
    global _DB_READY
    if not _DB_READY:
        skip_db = pytest.mark.skip(reason="Database unavailable — db_integration tests require PostgreSQL")
        for item in items:
            if "db_integration" in item.keywords:
                item.add_marker(skip_db)


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
    conn = get_connection()
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