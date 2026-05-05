from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StockRecord(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    sector: str
    market_cap: float
    avg_volume: float


class RedditCommentRecord(BaseModel):
    reddit_comment_id: str
    reddit_post_id: str
    author: str
    body_original: str
    body_translated: str | None = None
    detected_language: Literal["en", "zh", "unknown"] = "unknown"
    score: int = 0
    created_utc: datetime
    collected_at: datetime


class RedditPostRecord(BaseModel):
    reddit_id: str
    subreddit: str
    author: str
    title_original: str
    body_original: str
    title_translated: str | None = None
    body_translated: str | None = None
    detected_language: Literal["en", "zh", "unknown"] = "unknown"
    url: str
    permalink: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: datetime
    collected_at: datetime
    comments: list[RedditCommentRecord] = Field(default_factory=list)


class TickerMentionRecord(BaseModel):
    ticker: str
    reddit_post_id: str
    reddit_comment_id: str | None = None
    mention_source: Literal["post", "comment"]
    mention_count: int = 1
    created_utc: datetime


class StockPriceRecord(BaseModel):
    ticker: str
    price_date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float


class PostFeatureRecord(BaseModel):
    reddit_post_id: str
    ticker: str
    text_length: int
    title_length: int
    num_comments: int
    score: int
    upvote_ratio: float
    engagement_score: float
    sentiment_score: float
    bullish_score: float
    bearish_score: float
    hype_score: float
    catalyst_score: float
    risk_language_score: float
    language: str
    created_utc: datetime
    subreddit: str
    summary: str
    bullish_factors: list[str] = Field(default_factory=list)
    bearish_factors: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class HistoricalReturnRecord(BaseModel):
    reddit_post_id: str
    ticker: str
    signal_date: datetime
    price_at_post: float
    return_1d: float
    return_3d: float
    return_5d: float
    return_10d: float
    max_drawdown_10d: float
    beat_spy_5d: bool
    created_at: datetime


class DailySignalRecord(BaseModel):
    signal_date: datetime
    ticker: str
    current_price: float
    mention_count_today: int
    mention_count_7d_avg: float
    mention_spike: float
    sentiment_score: float
    historical_win_rate_5d: float
    avg_return_5d_after_similar_posts: float
    signal_score: float
    risk_score: float
    confidence: float
    label: str
    one_line_reason: str
    created_at: datetime
    sample_size: int
    downside_rate_5d: float
    cross_subreddit_confirmation: float
    sentiment_label: str


class Snapshot(BaseModel):
    generated_at: datetime
    stocks: list[StockRecord]
    reddit_posts: list[RedditPostRecord]
    reddit_comments: list[RedditCommentRecord]
    ticker_mentions: list[TickerMentionRecord]
    stock_prices: list[StockPriceRecord]
    post_features: list[PostFeatureRecord]
    historical_returns: list[HistoricalReturnRecord]
    daily_signals: list[DailySignalRecord]
    warnings: list[str] = Field(default_factory=list)


class DashboardRow(BaseModel):
    ticker: str
    company: str
    current_price: float
    change_1d_pct: float
    change_5d_pct: float
    reddit_post_count_today: int
    mention_spike: float
    sentiment: float
    historical_win_rate: float
    avg_5d_return_after_similar_posts: float
    signal_score: float
    risk_score: float
    confidence: float
    label: str
    one_line_reason: str
    subreddits: list[str]
    sample_size: int


class ExpandedPost(BaseModel):
    reddit_id: str
    ticker: str
    title_original: str
    title_translated: str | None = None
    subreddit: str
    post_timestamp: datetime
    summary: str
    bullish_factors: list[str]
    bearish_factors: list[str]
    risk_flags: list[str]
    historical_results: dict[str, float | int]
    why_this_score: str


class TickerDetail(BaseModel):
    ticker: str
    company: str
    current_price: float
    signal_score: float
    risk_score: float
    confidence: float
    label: str
    one_line_reason: str
    explanation: str
    recent_posts: list[ExpandedPost]
    historical_summary: dict[str, float | int]
    warnings: list[str] = Field(default_factory=list)

