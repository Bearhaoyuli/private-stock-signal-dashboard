from app.core.config import get_settings
from app.services.pipeline import get_or_build_snapshot


if __name__ == "__main__":
    snapshot = get_or_build_snapshot(get_settings(), refresh=True)
    print(f"Ingested {len(snapshot.reddit_posts)} posts and {len(snapshot.reddit_comments)} comments.")
    if snapshot.warnings:
        print("Warnings:")
        for warning in snapshot.warnings:
            print(f"- {warning}")

