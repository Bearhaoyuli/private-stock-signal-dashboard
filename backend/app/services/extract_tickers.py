from __future__ import annotations

import csv
import re
from pathlib import Path

BLOCKED_WORDS = {
    "A",
    "I",
    "IT",
    "ON",
    "IN",
    "FOR",
    "BY",
    "ALL",
    "ARE",
    "CAN",
    "CEO",
    "CFO",
    "USA",
    "GDP",
    "CPI",
    "AI",
    "DD",
    "YOLO",
    "IMO",
    "LOL",
}

FINANCE_CONTEXT_WORDS = {
    "earnings",
    "guidance",
    "revenue",
    "margin",
    "price",
    "valuation",
    "bullish",
    "bearish",
    "position",
    "shares",
    "breakout",
    "contract",
    "buyback",
    "guidance",
    "财报",
    "利好",
    "增长",
    "回购",
    "退市",
    "做空",
}

TICKER_PATTERN = re.compile(r"(?<![A-Z])\$?([A-Z]{1,5})(?![A-Z])")


def load_ticker_whitelist() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent.parent / "data" / "ticker_whitelist.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {row["ticker"]: row for row in reader}


def text_has_finance_context(text: str) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in FINANCE_CONTEXT_WORDS)


def extract_tickers(text: str, whitelist: dict[str, dict[str, str]]) -> list[str]:
    if not text:
        return []

    matches: list[str] = []
    finance_context = text_has_finance_context(text)
    for candidate in TICKER_PATTERN.findall(text):
        symbol = candidate.upper()
        if symbol in BLOCKED_WORDS:
            continue
        if symbol not in whitelist:
            continue
        if f"${symbol}" in text or symbol in text and finance_context:
            matches.append(symbol)
    return sorted(set(matches))

