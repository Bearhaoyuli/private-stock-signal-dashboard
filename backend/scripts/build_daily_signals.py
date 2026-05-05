from app.core.config import get_settings
from app.services.pipeline import build_snapshot


if __name__ == "__main__":
    snapshot = build_snapshot(get_settings())
    print(f"Built {len(snapshot.daily_signals)} daily signals.")
    for signal in snapshot.daily_signals[:5]:
        print(signal.ticker, signal.label, signal.signal_score, signal.risk_score)

