from app.core.config import get_settings
from app.services.mock_reddit_client import MockRedditClient


if __name__ == "__main__":
    posts = MockRedditClient(get_settings().subreddits).fetch_posts()
    print(f"Generated {len(posts)} mock posts.")

