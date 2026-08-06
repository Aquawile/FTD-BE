"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.exceptions import AuthenticationError
from app.routes import filings, search, tickers, users
from app.auth.router import router as auth_router
from app.auth.middleware import AuthMiddleware

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

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

# Include routers
app.include_router(auth_router)
app.include_router(tickers.router)
app.include_router(filings.router)
app.include_router(search.router)
app.include_router(users.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
