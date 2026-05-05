from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import pandas as pd

from app.models.schemas import (
    DailySignalRecord,
    HistoricalReturnRecord,
    PostFeatureRecord,
    RedditPostRecord,
    StockPriceRecord,
    StockRecord,
)
from app.services.nlp import repeated_language_score


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _returns_lookup(prices: list[StockPriceRecord]) -> dict[str, pd.DataFrame]:
    grouped: dict[str, list[StockPriceRecord]] = defaultdict(list)
    for price in prices:
        grouped[price.ticker].append(price)

    frames: dict[str, pd.DataFrame] = {}
    for ticker, records in grouped.items():
        frame = pd.DataFrame(
            {
                "price_date": [record.price_date.date() for record in records],
                "close": [record.close for record in records],
                "volume": [record.volume for record in records],
            }
        ).sort_values("price_date")
        frames[ticker] = frame.reset_index(drop=True)
    return frames


def calculate_historical_returns(
    posts: list[RedditPostRecord],
    features: list[PostFeatureRecord],
    prices: list[StockPriceRecord],
) -> list[HistoricalReturnRecord]:
    frames = _returns_lookup(prices)
    feature_map = {(feature.reddit_post_id, feature.ticker): feature for feature in features}
    spy_frame = frames.get("SPY")
    results: list[HistoricalReturnRecord] = []

    for feature in features:
        post = next((item for item in posts if item.reddit_id == feature.reddit_post_id), None)
        if post is None:
            continue
        frame = frames.get(feature.ticker)
        if frame is None or frame.empty:
            continue

        post_date = post.created_utc.date()
        start_idx = frame.index[frame["price_date"] >= post_date]
        if len(start_idx) == 0:
            continue
        start_idx = int(start_idx[0])
        if start_idx + 10 >= len(frame):
            continue

        base_close = float(frame.loc[start_idx, "close"])
        ret_1d = (float(frame.loc[start_idx + 1, "close"]) / base_close) - 1
        ret_3d = (float(frame.loc[start_idx + 3, "close"]) / base_close) - 1
        ret_5d = (float(frame.loc[start_idx + 5, "close"]) / base_close) - 1
        ret_10d = (float(frame.loc[start_idx + 10, "close"]) / base_close) - 1
        window = frame.loc[start_idx : start_idx + 10, "close"]
        max_drawdown = (float(window.min()) / base_close) - 1

        beat_spy_5d = False
        if spy_frame is not None and not spy_frame.empty:
            spy_start_idx = spy_frame.index[spy_frame["price_date"] >= post_date]
            if len(spy_start_idx) and int(spy_start_idx[0]) + 5 < len(spy_frame):
                spy_start = int(spy_start_idx[0])
                spy_base = float(spy_frame.loc[spy_start, "close"])
                spy_ret_5d = (float(spy_frame.loc[spy_start + 5, "close"]) / spy_base) - 1
                beat_spy_5d = ret_5d > spy_ret_5d

        results.append(
            HistoricalReturnRecord(
                reddit_post_id=feature.reddit_post_id,
                ticker=feature.ticker,
                signal_date=datetime.combine(post_date, datetime.min.time(), tzinfo=UTC),
                price_at_post=round(base_close, 2),
                return_1d=ret_1d,
                return_3d=ret_3d,
                return_5d=ret_5d,
                return_10d=ret_10d,
                max_drawdown_10d=max_drawdown,
                beat_spy_5d=beat_spy_5d,
                created_at=datetime.now(UTC),
            )
        )
    return results


def build_daily_signals(
    posts: list[RedditPostRecord],
    features: list[PostFeatureRecord],
    returns: list[HistoricalReturnRecord],
    stocks: list[StockRecord],
    prices: list[StockPriceRecord],
) -> list[DailySignalRecord]:
    stock_map = {stock.ticker: stock for stock in stocks}
    price_frames = _returns_lookup(prices)
    today = datetime.now(UTC).date()
    post_map = {post.reddit_id: post for post in posts}
    returns_by_post = {(item.reddit_post_id, item.ticker): item for item in returns}

    features_by_ticker: dict[str, list[PostFeatureRecord]] = defaultdict(list)
    for feature in features:
        features_by_ticker[feature.ticker].append(feature)

    signals: list[DailySignalRecord] = []
    for ticker, ticker_features in features_by_ticker.items():
        today_features = [
            feature
            for feature in ticker_features
            if post_map[feature.reddit_post_id].created_utc.date() == today
        ]
        if not today_features:
            continue

        stock = stock_map[ticker]
        frame = price_frames[ticker]
        latest_close = float(frame.iloc[-1]["close"])
        latest_volume = float(frame.iloc[-1]["volume"])
        volume_20d_avg = float(frame.iloc[-20:]["volume"].mean())
        volume_spike = clamp((latest_volume / max(volume_20d_avg, 1.0) - 1.0) / 1.5)
        recent_5d_runup = clamp(((latest_close / float(frame.iloc[-6]["close"])) - 1.0) / 0.15)

        mention_count_today = len(today_features)
        prior_window_start = today - timedelta(days=7)
        mention_history = [
            feature
            for feature in ticker_features
            if prior_window_start <= post_map[feature.reddit_post_id].created_utc.date() < today
        ]
        mention_count_7d_avg = len(mention_history) / 7 if mention_history else 0.0
        mention_spike = mention_count_today / max(mention_count_7d_avg, 1.0)

        sentiment_score = sum(feature.sentiment_score for feature in today_features) / mention_count_today
        bullish_score = sum(feature.bullish_score for feature in today_features) / mention_count_today
        bearish_score = sum(feature.bearish_score for feature in today_features) / mention_count_today
        hype_score = sum(feature.hype_score for feature in today_features) / mention_count_today
        catalyst_score = sum(feature.catalyst_score for feature in today_features) / mention_count_today
        engagement_quality = sum(feature.engagement_score for feature in today_features) / mention_count_today
        unique_subreddits = {feature.subreddit for feature in today_features}
        cross_subreddit = clamp(len(unique_subreddits) / 3)

        comparison_set = [
            ret
            for ret in returns
            if ret.ticker == ticker and ret.signal_date.date() < today
        ]
        current_sentiment_bucket = round((sentiment_score + 1) * 2) / 2
        current_hype_bucket = round(hype_score * 4) / 4
        current_engagement_bucket = round(engagement_quality * 4) / 4

        similar_returns: list[HistoricalReturnRecord] = []
        for ret in comparison_set:
            feature = next(
                (
                    candidate
                    for candidate in ticker_features
                    if candidate.reddit_post_id == ret.reddit_post_id
                ),
                None,
            )
            if feature is None:
                continue
            if abs(round((feature.sentiment_score + 1) * 2) / 2 - current_sentiment_bucket) > 0.5:
                continue
            if abs(round(feature.hype_score * 4) / 4 - current_hype_bucket) > 0.5:
                continue
            if abs(round(feature.engagement_score * 4) / 4 - current_engagement_bucket) > 0.5:
                continue
            similar_returns.append(ret)

        if len(similar_returns) < 6:
            similar_returns = comparison_set

        sample_size = len(similar_returns)
        if sample_size:
            win_rate = sum(1 for ret in similar_returns if ret.return_5d > 0) / sample_size
            avg_return_5d = sum(ret.return_5d for ret in similar_returns) / sample_size
            downside_rate = sum(1 for ret in similar_returns if ret.return_5d < -0.05) / sample_size
        else:
            win_rate = 0.5
            avg_return_5d = 0.0
            downside_rate = 0.5

        repeated_score = repeated_language_score(" ".join(post_map[item.reddit_post_id].title_original for item in today_features))
        low_liquidity = clamp(1 - min(stock.avg_volume / 50_000_000, 1.0))
        penny_risk = clamp((10 - latest_close) / 10) if latest_close < 10 else 0.0
        market_cap_risk = clamp((20_000_000_000 - stock.market_cap) / 20_000_000_000)
        concentrated_discussion = clamp(1 - min(mention_count_today / 3, 1.0))

        signal_score = 100 * (
            (win_rate * 0.20)
            + (clamp(avg_return_5d / 0.10) * 0.20)
            + (clamp((mention_spike - 1) / 3) * 0.15)
            + (((sentiment_score + 1) / 2) * 0.15)
            + (volume_spike * 0.10)
            + (catalyst_score * 0.10)
            + (engagement_quality * 0.05)
            + (cross_subreddit * 0.05)
        )

        risk_score = 100 * (
            (hype_score * 0.20)
            + (recent_5d_runup * 0.20)
            + (low_liquidity * 0.15)
            + (max(penny_risk, market_cap_risk) * 0.15)
            + ((1 - catalyst_score) * 0.10)
            + (repeated_score * 0.10)
            + (concentrated_discussion * 0.10)
        )

        if sample_size >= 30 and len(unique_subreddits) >= 2:
            confidence = 85
        elif sample_size >= 10:
            confidence = 60
        else:
            confidence = 30

        if signal_score >= 75 and risk_score < 50:
            label = "Strong Research Signal"
        elif signal_score >= 60 and risk_score < 65:
            label = "Research"
        elif risk_score >= 75:
            label = "Too Hypey"
        elif signal_score < 40 or downside_rate > 0.45:
            label = "Avoid"
        else:
            label = "Watch"

        sentiment_label = "Bullish" if sentiment_score > 0.2 else "Bearish" if sentiment_score < -0.2 else "Mixed"
        one_line_reason = _build_reason(
            ticker=ticker,
            win_rate=win_rate,
            avg_return_5d=avg_return_5d,
            mention_spike=mention_spike,
            catalyst_score=catalyst_score,
            hype_score=hype_score,
            downside_rate=downside_rate,
        )

        signals.append(
            DailySignalRecord(
                signal_date=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
                ticker=ticker,
                current_price=round(latest_close, 2),
                mention_count_today=mention_count_today,
                mention_count_7d_avg=round(mention_count_7d_avg, 2),
                mention_spike=round(mention_spike, 2),
                sentiment_score=round(sentiment_score, 3),
                historical_win_rate_5d=round(win_rate, 3),
                avg_return_5d_after_similar_posts=round(avg_return_5d, 4),
                signal_score=round(signal_score, 1),
                risk_score=round(risk_score, 1),
                confidence=confidence,
                label=label,
                one_line_reason=one_line_reason,
                created_at=datetime.now(UTC),
                sample_size=sample_size,
                downside_rate_5d=round(downside_rate, 3),
                cross_subreddit_confirmation=round(cross_subreddit, 3),
                sentiment_label=sentiment_label,
            )
        )

    return sorted(signals, key=lambda item: (-item.signal_score, item.risk_score, item.ticker))


def _build_reason(
    *,
    ticker: str,
    win_rate: float,
    avg_return_5d: float,
    mention_spike: float,
    catalyst_score: float,
    hype_score: float,
    downside_rate: float,
) -> str:
    if downside_rate > 0.45:
        return f"{ticker} has weak historical follow-through and an elevated downside rate after similar posts."
    if win_rate > 0.62 and avg_return_5d > 0.03:
        return f"{ticker} has above-baseline 5D follow-through after similar posts and catalysts look tangible."
    if hype_score > 0.5:
        return f"{ticker} is seeing a sharp mention spike, but crowd language is running hotter than fundamentals."
    if mention_spike > 1.5 and catalyst_score > 0.4:
        return f"{ticker} is getting fresh attention with at least one real catalyst signal behind the discussion."
    return f"{ticker} is worth monitoring, but the historical sample is still limited."

