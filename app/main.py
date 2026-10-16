"""FastAPI application entry point."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.exceptions import AuthenticationError, AuthenticationInternalError
from app.auth.models import ErrorResponse
from app.routes import dashboard, filings, search, tickers, users, workspaces, alerts, admin
from app.auth.router import router as auth_router
from app.auth.middleware import AuthMiddleware
from app.middleware.audit_middleware import AuditLogMiddleware
from app.services.db_access_counter import get_counters
from app.logging_config import setup_logging
from app.services.exceptions import (
    DataValidationError,
    FilingNotFoundError,
    TickerNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserValidationError,
)

logger = logging.getLogger("app")
setup_logging()

app = FastAPI(
    title="FTD Lakehouse API",
    description="Read-only API for financial research data: prices, news, SEC filings, timeline.",
    version="0.1.0",
)


# CORS — lock to local dev frontend origin. Production origin set later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Auth middleware — intercepts every request before route handlers
app.add_middleware(AuthMiddleware)

# Audit logging middleware — wraps AFTER AuthMiddleware so request.state is populated
app.add_middleware(AuditLogMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(tickers.router)
app.include_router(filings.router)
app.include_router(search.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.on_event("startup")
def _warm_vectorized_count() -> None:
    """Fill the chunk-count cache in the background so the first
    /dashboard/stats after a restart doesn't pay the ~13s GCS scan."""
    import threading

    from app.services.vectorized_gcs import count_vectorized_content

    def _warm() -> None:
        try:
            count_vectorized_content()
        except Exception:
            logger.warning("Vectorized count warm-up failed", exc_info=True)

    threading.Thread(target=_warm, name="warm-vectorized-count", daemon=True).start()


@app.get("/health")
def health_check() -> dict:
    counters = get_counters()
    has_db_hits = any(v > 0 for v in counters.values())
    return {
        "status": "ok",
        "db_access_counters": counters,
        "db_access_detected": has_db_hits,
    }


def _load_version_metadata() -> dict[str, str]:
    """Load version metadata from version.json written during deployment."""
    version_path = Path("/home/isabellabutera/version.json")
    if version_path.exists():
        try:
            with version_path.open("r") as f:
                data = json.load(f)
            return {
                "commit_sha": data.get("commit_sha", "unknown"),
                "branch": data.get("branch", "unknown"),
                "commit_message": data.get("commit_message", "unknown"),
                "deployed_at": data.get("deployed_at", "unknown"),
                "environment": data.get("environment", "unknown"),
                "workflow_run_id": data.get("workflow_run_id", "unknown"),
            }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load version.json: %s", e)
    return {
        "commit_sha": "unknown",
        "branch": "unknown",
        "commit_message": "unknown",
        "deployed_at": "unknown",
        "environment": "unknown",
        "workflow_run_id": "unknown",
    }


@app.get("/version")
def version_check() -> dict[str, str]:
    return _load_version_metadata()


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    logger.warning("http:user_not_found detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc) or "User not found"},
    )


@app.exception_handler(UserAlreadyExistsError)
async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError) -> JSONResponse:
    logger.warning("http:user_already_exists detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc) or "User already exists"},
    )


@app.exception_handler(UserValidationError)
async def user_validation_error_handler(request: Request, exc: UserValidationError) -> JSONResponse:
    logger.warning("http:user_validation_error detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc) or "Validation error"},
    )


@app.exception_handler(TickerNotFoundError)
async def ticker_not_found_handler(request: Request, exc: TickerNotFoundError) -> JSONResponse:
    logger.warning("http:ticker_not_found detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc) or "Ticker not found"},
    )


@app.exception_handler(FilingNotFoundError)
async def filing_not_found_handler(request: Request, exc: FilingNotFoundError) -> JSONResponse:
    logger.warning("http:filing_not_found detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc) or "Filing not found"},
    )


@app.exception_handler(DataValidationError)
async def data_validation_error_handler(request: Request, exc: DataValidationError) -> JSONResponse:
    logger.warning("http:data_validation_error detail=%s", exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc) or "Validation error"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("http:unhandled_exception path=%s error=%s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )