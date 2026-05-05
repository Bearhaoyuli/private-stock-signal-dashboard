from app.services.extract_tickers import load_ticker_whitelist
from app.services.pipeline import _build_stock_catalog
from app.services.price_service import fetch_stock_prices


if __name__ == "__main__":
    catalog = _build_stock_catalog(load_ticker_whitelist())
    prices = fetch_stock_prices(catalog, use_live_prices=False)
    print(f"Generated {len(prices)} stock price rows.")

