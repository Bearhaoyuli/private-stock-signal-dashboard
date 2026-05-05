from app.core.config import get_settings
from app.services.reddit_client import RedditClientFactory


if __name__ == "__main__":
    posts, warnings = RedditClientFactory(get_settings()).fetch_posts()
    print(f"Fetched {len(posts)} posts.")
    for warning in warnings:
        print(f"- {warning}")

