from app.services.extract_tickers import extract_tickers, load_ticker_whitelist


if __name__ == "__main__":
    whitelist = load_ticker_whitelist()
    sample = "AAPL still looks undervalued while NVDA hype is overheating and AI alone is not a ticker."
    print(extract_tickers(sample, whitelist))

