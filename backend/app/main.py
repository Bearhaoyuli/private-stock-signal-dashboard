from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.services.pipeline import (
    build_dashboard_rows,
    build_ticker_detail,
    get_or_build_snapshot,
)


settings = get_settings()
app = FastAPI(
    title="Reddit Stock Research Signal API",
    version="0.1.0",
    description="Mock-first backend for a private personal stock research signal dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard(
    subreddit: str | None = Query(default=None),
    window: str = Query(default="Today"),
    min_signal: int = Query(default=0, ge=0, le=100),
    search: str | None = Query(default=None),
) -> dict:
    snapshot = get_or_build_snapshot(settings)
    rows = build_dashboard_rows(snapshot)

    filtered = rows
    if subreddit:
        filtered = [row for row in filtered if subreddit in row.subreddits]
    if search:
        needle = search.lower()
        filtered = [
            row
            for row in filtered
            if needle in row.ticker.lower() or needle in row.company.lower()
        ]
    filtered = [row for row in filtered if row.signal_score >= min_signal]
    return {
        "window": window,
        "rows": [row.model_dump(mode="json") for row in filtered],
        "warnings": snapshot.warnings,
        "generated_at": snapshot.generated_at,
    }


@app.get("/api/ticker/{ticker}")
def get_ticker(ticker: str) -> dict:
    snapshot = get_or_build_snapshot(settings)
    detail = build_ticker_detail(snapshot, ticker.upper())
    if detail is None:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return detail.model_dump(mode="json")


@app.post("/api/ingest/reddit")
def ingest_reddit() -> dict:
    snapshot = get_or_build_snapshot(settings, refresh=True)
    return {
        "message": "Reddit ingestion completed.",
        "posts": len(snapshot.reddit_posts),
        "comments": len(snapshot.reddit_comments),
        "warnings": snapshot.warnings,
    }


@app.post("/api/jobs/build-signals")
def build_signals() -> dict:
    snapshot = get_or_build_snapshot(settings, refresh=True)
    return {
        "message": "Signals built.",
        "signals": len(snapshot.daily_signals),
        "generated_at": snapshot.generated_at,
        "warnings": snapshot.warnings,
    }

