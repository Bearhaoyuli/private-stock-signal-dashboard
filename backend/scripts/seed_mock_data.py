from app.core.config import get_settings
from app.services.pipeline import get_or_build_snapshot


if __name__ == "__main__":
    snapshot = get_or_build_snapshot(get_settings(), refresh=True)
    print(f"Seeded snapshot at {snapshot.generated_at.isoformat()}.")
