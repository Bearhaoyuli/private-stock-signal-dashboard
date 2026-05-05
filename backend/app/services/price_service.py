from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.models.schemas import StockPriceRecord, StockRecord

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


MOCK_PRICE_PROFILES = {
    "AAPL": {"base": 211.0, "drift": 0.0024, "volatility": 0.012, "volume": 62_000_000},
    "NVDA": {"base": 118.0, "drift": 0.0038, "volatility": 0.026, "volume": 52_000_000},
    "TSLA": {"base": 176.0, "drift": -0.0015, "volatility": 0.031, "volume": 96_000_000},
    "AMD": {"base": 154.0, "drift": 0.0031, "volatility": 0.018, "volume": 61_000_000},
    "SOFI": {"base": 7.65, "drift": -0.0008, "volatility": 0.028, "volume": 47_000_000},
    "SPY": {"base": 505.0, "drift": 0.0012, "volatility": 0.009, "volume": 78_000_000},
}


def _business_dates(periods: int = 40) -> pd.DatetimeIndex:
    end = pd.Timestamp(datetime.now(UTC).date())
    return pd.bdate_range(end=end, periods=periods)


def _synthetic_prices_for_ticker(ticker: str, periods: int = 40) -> list[StockPriceRecord]:
    profile = MOCK_PRICE_PROFILES.get(ticker, MOCK_PRICE_PROFILES["SPY"])
    dates = _business_dates(periods)
    seed = abs(hash(ticker)) % 2**32
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=profile["drift"], scale=profile["volatility"], size=len(dates))
    close_prices = profile["base"] * np.cumprod(1 + returns)
    open_prices = close_prices / (1 + rng.normal(0, 0.003, len(dates)))
    high_prices = np.maximum(open_prices, close_prices) * (1 + rng.uniform(0.001, 0.02, len(dates)))
    low_prices = np.minimum(open_prices, close_prices) * (1 - rng.uniform(0.001, 0.018, len(dates)))
    volumes = profile["volume"] * (1 + rng.normal(0, 0.18, len(dates)))

    return [
        StockPriceRecord(
            ticker=ticker,
            price_date=date.to_pydatetime().replace(tzinfo=UTC),
            open=round(float(open_price), 2),
            high=round(float(high_price), 2),
            low=round(float(low_price), 2),
            close=round(float(close_price), 2),
            volume=float(max(volume, profile["volume"] * 0.35)),
            adjusted_close=round(float(close_price), 2),
        )
        for date, open_price, high_price, low_price, close_price, volume in zip(
            dates,
            open_prices,
            high_prices,
            low_prices,
            close_prices,
            volumes,
            strict=True,
        )
    ]


def fetch_stock_prices(stocks: list[StockRecord], use_live_prices: bool = False) -> list[StockPriceRecord]:
    tickers = sorted({stock.ticker for stock in stocks} | {"SPY"})
    if use_live_prices and yf is not None:
        try:  # pragma: no cover
            downloaded = yf.download(
                tickers=tickers,
                period="3mo",
                interval="1d",
                auto_adjust=False,
                progress=False,
                group_by="ticker",
            )
            if not downloaded.empty:
                prices: list[StockPriceRecord] = []
                for ticker in tickers:
                    ticker_frame = downloaded[ticker].dropna()
                    for idx, row in ticker_frame.iterrows():
                        prices.append(
                            StockPriceRecord(
                                ticker=ticker,
                                price_date=idx.to_pydatetime().replace(tzinfo=UTC),
                                open=round(float(row["Open"]), 2),
                                high=round(float(row["High"]), 2),
                                low=round(float(row["Low"]), 2),
                                close=round(float(row["Close"]), 2),
                                volume=float(row["Volume"]),
                                adjusted_close=round(float(row.get("Adj Close", row["Close"])), 2),
                            )
                        )
                if prices:
                    return prices
        except Exception:
            pass

    synthetic: list[StockPriceRecord] = []
    for ticker in tickers:
        synthetic.extend(_synthetic_prices_for_ticker(ticker))
    return synthetic

