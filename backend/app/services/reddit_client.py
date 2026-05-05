from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.config import Settings
from app.models.schemas import RedditPostRecord
from app.services.mock_reddit_client import MockRedditClient

try:
    import praw
except ImportError:  # pragma: no cover
    praw = None


logger = logging.getLogger(__name__)


class RedditClientFactory:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch_posts(self) -> tuple[list[RedditPostRecord], list[str]]:
        warnings: list[str] = []
        if not self.settings.enable_reddit_live:
            warnings.append("Reddit live mode disabled. Using mock Reddit seed data.")
            return MockRedditClient(self.settings.subreddits).fetch_posts(), warnings

        if not self.settings.has_reddit_credentials or praw is None:
            warnings.append(
                "ENABLE_REDDIT_LIVE=true but Reddit credentials are missing or PRAW is unavailable. Falling back to mock mode."
            )
            return MockRedditClient(self.settings.subreddits).fetch_posts(), warnings

        try:
            client = praw.Reddit(
                client_id=self.settings.reddit_client_id,
                client_secret=self.settings.reddit_client_secret,
                username=self.settings.reddit_username,
                password=self.settings.reddit_password,
                user_agent=self.settings.reddit_user_agent,
            )
            posts: list[RedditPostRecord] = []
            for subreddit_name in self.settings.subreddits:
                subreddit = client.subreddit(subreddit_name)
                for submission in subreddit.new(limit=25):
                    posts.append(
                        RedditPostRecord(
                            reddit_id=submission.id,
                            subreddit=subreddit_name,
                            author=str(submission.author or "unknown"),
                            title_original=submission.title,
                            body_original=submission.selftext or "",
                            url=submission.url,
                            permalink=f"https://reddit.com{submission.permalink}",
                            score=submission.score,
                            upvote_ratio=getattr(submission, "upvote_ratio", 0.5) or 0.5,
                            num_comments=submission.num_comments,
                            created_utc=datetime.fromtimestamp(submission.created_utc, tz=UTC),
                            collected_at=datetime.now(UTC),
                        )
                    )
            if not posts:
                warnings.append("Reddit live mode returned no posts. Falling back to mock mode.")
                return MockRedditClient(self.settings.subreddits).fetch_posts(), warnings
            return posts, warnings
        except Exception as exc:  # pragma: no cover
            logger.exception("Live Reddit fetch failed")
            warnings.append(f"Live Reddit fetch failed: {exc}. Falling back to mock mode.")
            return MockRedditClient(self.settings.subreddits).fetch_posts(), warnings
