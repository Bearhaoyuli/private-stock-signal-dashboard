from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import cycle

from app.models.schemas import RedditCommentRecord, RedditPostRecord


class MockRedditClient:
    def __init__(self, subreddits: list[str]):
        self.subreddits = subreddits

    def fetch_posts(self) -> list[RedditPostRecord]:
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        subreddit_cycle = cycle(self.subreddits or ["stocks", "investing", "美股"])

        scenarios = [
            {
                "ticker": "AAPL",
                "language": "en",
                "title": "AAPL still looks undervalued after services growth and another buyback signal",
                "body": "Apple keeps showing revenue growth, margin expansion, and buyback support. This feels like a steady breakout instead of a hype squeeze.",
                "score": 412,
                "comments": 84,
                "upvote_ratio": 0.93,
            },
            {
                "ticker": "NVDA",
                "language": "en",
                "title": "NVDA is going to moon again, next squeeze is here",
                "body": "This rocket still has fuel, everyone is loading up, and it feels like the next NVDA run. Incredible AI demand but the setup is crowded.",
                "score": 982,
                "comments": 201,
                "upvote_ratio": 0.88,
            },
            {
                "ticker": "TSLA",
                "language": "en",
                "title": "TSLA bounce looks weak with delivery pressure and more downside risk",
                "body": "Tesla still has delivery pressure, debt concerns around execution, and the bounce looks more like sentiment repair than durable upside.",
                "score": 295,
                "comments": 96,
                "upvote_ratio": 0.84,
            },
            {
                "ticker": "AMD",
                "language": "zh",
                "title": "AMD 业绩超预期，数据中心增长加速，感觉还有突破空间。",
                "body": "AMD 这次财报是明显利好，业绩超预期，数据中心增长很快，估值也不算贵。",
                "score": 366,
                "comments": 58,
                "upvote_ratio": 0.91,
            },
            {
                "ticker": "SOFI",
                "language": "zh",
                "title": "SOFI 高位接盘风险太大，盈利质量一般，还要小心稀释。",
                "body": "最近讨论太热，但基本面没有想象中强，还要注意稀释和负债问题。",
                "score": 228,
                "comments": 67,
                "upvote_ratio": 0.81,
            },
        ]

        day_offsets = [0, 0, 1, 2, 3, 5, 7, 9, 12, 15, 19, 24]
        posts: list[RedditPostRecord] = []

        for scenario_index, scenario in enumerate(scenarios):
            for offset_index, day_offset in enumerate(day_offsets):
                created_at = now - timedelta(days=day_offset, hours=(scenario_index * 2 + offset_index) % 9)
                ticker = scenario["ticker"]
                post_id = f"mock_{ticker.lower()}_{offset_index + 1}"
                multiplier = 1 + ((offset_index % 4) * 0.08)
                score = int(scenario["score"] * multiplier)
                comments = int(scenario["comments"] * (0.8 + (offset_index % 3) * 0.2))
                post = RedditPostRecord(
                    reddit_id=post_id,
                    subreddit=next(subreddit_cycle),
                    author=f"{ticker.lower()}_analyst_{offset_index + 1}",
                    title_original=scenario["title"],
                    body_original=scenario["body"],
                    url=f"https://example.com/{post_id}",
                    permalink=f"/r/mock/{post_id}",
                    score=score,
                    upvote_ratio=max(0.55, min(0.98, scenario["upvote_ratio"] - (offset_index * 0.01))),
                    num_comments=comments,
                    created_utc=created_at,
                    collected_at=now,
                )
                post.comments = [
                    RedditCommentRecord(
                        reddit_comment_id=f"{post_id}_c1",
                        reddit_post_id=post_id,
                        author=f"commenter_{offset_index + 1}",
                        body_original=self._comment_text(ticker, scenario["language"], positive=offset_index % 2 == 0),
                        score=max(4, 18 - offset_index),
                        created_utc=created_at + timedelta(minutes=25),
                        collected_at=now,
                    ),
                    RedditCommentRecord(
                        reddit_comment_id=f"{post_id}_c2",
                        reddit_post_id=post_id,
                        author=f"skeptic_{offset_index + 1}",
                        body_original=self._comment_text(ticker, scenario["language"], positive=False),
                        score=max(2, 11 - offset_index),
                        created_utc=created_at + timedelta(minutes=47),
                        collected_at=now,
                    ),
                ]
                posts.append(post)
        return sorted(posts, key=lambda item: item.created_utc, reverse=True)

    @staticmethod
    def _comment_text(ticker: str, language: str, *, positive: bool) -> str:
        if language == "zh":
            return (
                f"{ticker} 这里还有利好，增长和回购都在。"
                if positive
                else f"{ticker} 也别忽略风险，负债和高位接盘问题还在。"
            )
        return (
            f"{ticker} still has a real catalyst here with growth and margin support."
            if positive
            else f"{ticker} still looks crowded and downside risk is not gone."
        )

