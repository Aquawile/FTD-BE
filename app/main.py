"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import filings, search, tickers
from app.auth.router import router as auth_router

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

# Include routers
app.include_router(auth_router)
app.include_router(tickers.router)
app.include_router(filings.router)
app.include_router(search.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
