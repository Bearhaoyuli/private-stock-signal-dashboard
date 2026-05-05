from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from supabase import Client, create_client

from app.core.config import Settings
from app.models.schemas import (
    DashboardRow,
    ExpandedPost,
    PostFeatureRecord,
    RedditCommentRecord,
    RedditPostRecord,
    Snapshot,
    StockRecord,
    TickerDetail,
    TickerMentionRecord,
)
from app.services.detect_translate_language import detect_language, translate_text
from app.services.extract_tickers import extract_tickers, load_ticker_whitelist
from app.services.nlp import analyze_text
from app.services.price_service import fetch_stock_prices
from app.services.reddit_client import RedditClientFactory
from app.services.scoring import build_daily_signals, calculate_historical_returns
from app.services.store import LocalSnapshotStore


def _build_stock_catalog(whitelist: dict[str, dict[str, str]]) -> list[StockRecord]:
    return [
        StockRecord(
            ticker=ticker,
            company_name=data["company_name"],
            exchange=data["exchange"],
            sector=data["sector"],
            market_cap=float(data["market_cap"]),
            avg_volume=float(data["avg_volume"]),
        )
        for ticker, data in whitelist.items()
        if ticker != "SPY"
    ]


def _enrich_post_language(post: RedditPostRecord, settings: Settings) -> RedditPostRecord:
    post.detected_language = detect_language(f"{post.title_original}\n{post.body_original}")
    if post.detected_language == "zh":
        post.title_translated = translate_text(
            post.title_original,
            "zh",
            api_key=settings.openai_api_key,
            enable_translation=settings.enable_translation,
        )
        post.body_translated = translate_text(
            post.body_original,
            "zh",
            api_key=settings.openai_api_key,
            enable_translation=settings.enable_translation,
        )

    for comment in post.comments:
        _enrich_comment_language(comment, settings)
    return post


def _enrich_comment_language(comment: RedditCommentRecord, settings: Settings) -> RedditCommentRecord:
    comment.detected_language = detect_language(comment.body_original)
    if comment.detected_language == "zh":
        comment.body_translated = translate_text(
            comment.body_original,
            "zh",
            api_key=settings.openai_api_key,
            enable_translation=settings.enable_translation,
        )
    return comment


def _build_mentions_and_features(
    posts: list[RedditPostRecord],
    whitelist: dict[str, dict[str, str]],
) -> tuple[list[TickerMentionRecord], list[PostFeatureRecord]]:
    mentions: list[TickerMentionRecord] = []
    features: list[PostFeatureRecord] = []

    for post in posts:
        analysis_text = " ".join(
            part
            for part in [
                post.title_translated or post.title_original,
                post.body_translated or post.body_original,
            ]
            if part
        )
        tickers = extract_tickers(f"{post.title_original}\n{post.body_original}", whitelist)
        if not tickers:
            continue

        for ticker in tickers:
            mentions.append(
                TickerMentionRecord(
                    ticker=ticker,
                    reddit_post_id=post.reddit_id,
                    mention_source="post",
                    created_utc=post.created_utc,
                )
            )
            analysis = analyze_text(analysis_text)
            engagement_score = min(
                (
                    (post.score / 1000)
                    + (post.num_comments / 200)
                    + (post.upvote_ratio * 0.5)
                ),
                1.0,
            )
            features.append(
                PostFeatureRecord(
                    reddit_post_id=post.reddit_id,
                    ticker=ticker,
                    text_length=len(post.body_original),
                    title_length=len(post.title_original),
                    num_comments=post.num_comments,
                    score=post.score,
                    upvote_ratio=post.upvote_ratio,
                    engagement_score=round(engagement_score, 3),
                    sentiment_score=float(analysis["sentiment_score"]),
                    bullish_score=float(analysis["bullish_score"]),
                    bearish_score=float(analysis["bearish_score"]),
                    hype_score=float(analysis["hype_score"]),
                    catalyst_score=float(analysis["catalyst_score"]),
                    risk_language_score=float(analysis["risk_language_score"]),
                    language=post.detected_language,
                    created_utc=post.created_utc,
                    subreddit=post.subreddit,
                    summary=str(analysis["summary"]),
                    bullish_factors=list(analysis["bullish_factors"]),
                    bearish_factors=list(analysis["bearish_factors"]),
                    risk_flags=list(analysis["risk_flags"]),
                )
            )

        for comment in post.comments:
            comment_tickers = extract_tickers(comment.body_original, whitelist)
            for ticker in comment_tickers:
                mentions.append(
                    TickerMentionRecord(
                        ticker=ticker,
                        reddit_post_id=post.reddit_id,
                        reddit_comment_id=comment.reddit_comment_id,
                        mention_source="comment",
                        created_utc=comment.created_utc,
                    )
                )

    return mentions, features


def build_snapshot(settings: Settings) -> Snapshot:
    whitelist = load_ticker_whitelist()
    stock_catalog = _build_stock_catalog(whitelist)
    reddit_posts, warnings = RedditClientFactory(settings).fetch_posts()
    enriched_posts = [_enrich_post_language(post, settings) for post in reddit_posts]
    comments = [comment for post in enriched_posts for comment in post.comments]
    mentions, features = _build_mentions_and_features(enriched_posts, whitelist)
    prices = fetch_stock_prices(stock_catalog, use_live_prices=settings.enable_reddit_live)
    historical_returns = calculate_historical_returns(enriched_posts, features, prices)
    daily_signals = build_daily_signals(
        posts=enriched_posts,
        features=features,
        returns=historical_returns,
        stocks=stock_catalog,
        prices=prices,
    )
    return Snapshot(
        generated_at=datetime.now(UTC),
        stocks=stock_catalog,
        reddit_posts=enriched_posts,
        reddit_comments=comments,
        ticker_mentions=mentions,
        stock_prices=prices,
        post_features=features,
        historical_returns=historical_returns,
        daily_signals=daily_signals,
        warnings=warnings,
    )


def persist_snapshot_to_supabase(snapshot: Snapshot, settings: Settings) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return

    client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    _upsert(client, "stocks", [row.model_dump() for row in snapshot.stocks], "ticker")
    _upsert(client, "reddit_posts", [_serialize_post(post) for post in snapshot.reddit_posts], "reddit_id")
    _upsert(client, "reddit_comments", [row.model_dump(mode="json") for row in snapshot.reddit_comments], "reddit_comment_id")
    _upsert(client, "stock_prices", [row.model_dump(mode="json") for row in snapshot.stock_prices], "ticker,price_date")
    _upsert(client, "post_features", [row.model_dump(mode="json") for row in snapshot.post_features], "reddit_post_id,ticker")
    _upsert(client, "historical_returns", [row.model_dump(mode="json") for row in snapshot.historical_returns], "reddit_post_id,ticker")
    _upsert(client, "daily_signals", [row.model_dump(mode="json") for row in snapshot.daily_signals], "signal_date,ticker")


def _upsert(client: Client, table: str, rows: list[dict], on_conflict: str) -> None:
    if not rows:
        return
    client.table(table).upsert(rows, on_conflict=on_conflict).execute()


def _serialize_post(post: RedditPostRecord) -> dict:
    payload = post.model_dump(mode="json")
    payload.pop("comments", None)
    return payload


def get_or_build_snapshot(settings: Settings, *, refresh: bool = False) -> Snapshot:
    store = LocalSnapshotStore(settings.snapshot_path)
    if not refresh:
        cached = store.load()
        if cached:
            return cached

    snapshot = build_snapshot(settings)
    store.save(snapshot)
    persist_snapshot_to_supabase(snapshot, settings)
    return snapshot


def build_dashboard_rows(snapshot: Snapshot) -> list[DashboardRow]:
    stock_map = {stock.ticker: stock for stock in snapshot.stocks}
    price_map: dict[str, list] = defaultdict(list)
    for price in snapshot.stock_prices:
        price_map[price.ticker].append(price)

    feature_map: dict[str, list[PostFeatureRecord]] = defaultdict(list)
    for feature in snapshot.post_features:
        feature_map[feature.ticker].append(feature)

    rows: list[DashboardRow] = []
    for signal in snapshot.daily_signals:
        prices = sorted(price_map[signal.ticker], key=lambda item: item.price_date)
        latest = prices[-1]
        day_1 = prices[-2] if len(prices) > 1 else prices[-1]
        day_5 = prices[-6] if len(prices) > 5 else prices[0]
        subreddits = sorted(
            {
                feature.subreddit
                for feature in feature_map[signal.ticker]
                if feature.created_utc.date() == signal.signal_date.date()
            }
        )
        rows.append(
            DashboardRow(
                ticker=signal.ticker,
                company=stock_map[signal.ticker].company_name,
                current_price=signal.current_price,
                change_1d_pct=round((latest.close / day_1.close - 1) * 100, 2),
                change_5d_pct=round((latest.close / day_5.close - 1) * 100, 2),
                reddit_post_count_today=signal.mention_count_today,
                mention_spike=signal.mention_spike,
                sentiment=signal.sentiment_score,
                historical_win_rate=round(signal.historical_win_rate_5d * 100, 1),
                avg_5d_return_after_similar_posts=round(signal.avg_return_5d_after_similar_posts * 100, 2),
                signal_score=signal.signal_score,
                risk_score=signal.risk_score,
                confidence=signal.confidence,
                label=signal.label,
                one_line_reason=signal.one_line_reason,
                subreddits=subreddits,
                sample_size=signal.sample_size,
            )
        )
    return rows


def build_ticker_detail(snapshot: Snapshot, ticker: str) -> TickerDetail | None:
    signal = next((item for item in snapshot.daily_signals if item.ticker == ticker), None)
    stock = next((item for item in snapshot.stocks if item.ticker == ticker), None)
    if signal is None or stock is None:
        return None

    feature_map = {
        (feature.reddit_post_id, feature.ticker): feature
        for feature in snapshot.post_features
    }
    return_map = {
        (record.reddit_post_id, record.ticker): record
        for record in snapshot.historical_returns
    }
    recent_posts: list[ExpandedPost] = []
    for post in sorted(snapshot.reddit_posts, key=lambda item: item.created_utc, reverse=True):
        feature = feature_map.get((post.reddit_id, ticker))
        if feature is None:
            continue
        historical = return_map.get((post.reddit_id, ticker))
        why = (
            f"Sentiment {feature.sentiment_score:+.2f}, hype {feature.hype_score:.2f}, catalyst {feature.catalyst_score:.2f}, "
            f"engagement {feature.engagement_score:.2f}."
        )
        recent_posts.append(
            ExpandedPost(
                reddit_id=post.reddit_id,
                ticker=ticker,
                title_original=post.title_original,
                title_translated=post.title_translated,
                subreddit=post.subreddit,
                post_timestamp=post.created_utc,
                summary=feature.summary,
                bullish_factors=feature.bullish_factors,
                bearish_factors=feature.bearish_factors,
                risk_flags=feature.risk_flags,
                historical_results={
                    "return_1d": round((historical.return_1d if historical else 0) * 100, 2),
                    "return_3d": round((historical.return_3d if historical else 0) * 100, 2),
                    "return_5d": round((historical.return_5d if historical else 0) * 100, 2),
                    "return_10d": round((historical.return_10d if historical else 0) * 100, 2),
                    "sample_size": signal.sample_size,
                },
                why_this_score=why,
            )
        )
        if len(recent_posts) >= 6:
            break

    explanation = (
        f"{ticker} scored {signal.signal_score:.1f}/100 because recent posts show a {signal.sentiment_label.lower()} "
        f"tone, mention spike {signal.mention_spike:.2f}x, and a {signal.historical_win_rate_5d * 100:.0f}% 5D win rate "
        f"across {signal.sample_size} similar historical posts."
    )

    return TickerDetail(
        ticker=ticker,
        company=stock.company_name,
        current_price=signal.current_price,
        signal_score=signal.signal_score,
        risk_score=signal.risk_score,
        confidence=signal.confidence,
        label=signal.label,
        one_line_reason=signal.one_line_reason,
        explanation=explanation,
        recent_posts=recent_posts,
        historical_summary={
            "historical_win_rate_5d": round(signal.historical_win_rate_5d * 100, 1),
            "avg_return_5d_after_similar_posts": round(signal.avg_return_5d_after_similar_posts * 100, 2),
            "downside_rate_5d": round(signal.downside_rate_5d * 100, 1),
            "sample_size": signal.sample_size,
        },
        warnings=snapshot.warnings,
    )
