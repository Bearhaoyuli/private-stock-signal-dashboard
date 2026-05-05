from app.core.config import get_settings
from app.services.pipeline import build_snapshot


if __name__ == "__main__":
    snapshot = build_snapshot(get_settings())
    print(f"Calculated {len(snapshot.historical_returns)} historical return rows.")

