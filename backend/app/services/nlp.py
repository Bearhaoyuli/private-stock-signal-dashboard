from __future__ import annotations

from collections import Counter


BULLISH_TERMS = {
    "beat earnings",
    "guidance raised",
    "revenue growth",
    "margin expansion",
    "contract",
    "approval",
    "partnership",
    "buyback",
    "short squeeze",
    "undervalued",
    "breakout",
    "利好",
    "低估",
    "突破",
    "业绩超预期",
    "增长",
    "回购",
    "合作",
    "批准",
}

BEARISH_TERMS = {
    "dilution",
    "bankruptcy",
    "lawsuit",
    "missed earnings",
    "guidance cut",
    "debt",
    "fraud",
    "investigation",
    "delisting",
    "insider selling",
    "暴雷",
    "退市",
    "亏损",
    "做空",
    "诈骗",
    "调查",
    "破产",
    "稀释",
    "负债",
    "高位接盘",
}

HYPE_TERMS = {
    "moon",
    "rocket",
    "squeeze",
    "guaranteed",
    "all in",
    "yolo",
    "10x",
    "next nvda",
    "can't lose",
    "load up",
}

RISK_TERMS = {
    "volatile",
    "crowded",
    "speculative",
    "downside",
    "risk",
    "investigation",
    "dilution",
    "负债",
    "退市",
    "稀释",
}


def _count_terms(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def _normalize_hits(hit_count: int, max_hits: int = 4) -> float:
    return min(hit_count / max_hits, 1.0)


def summarize_text(text: str, sentiment_score: float, bullish_hits: int, bearish_hits: int) -> str:
    if bullish_hits > bearish_hits and sentiment_score > 0.2:
        return "Discussion leans constructive and focuses on concrete upside catalysts."
    if bearish_hits > bullish_hits and sentiment_score < -0.2:
        return "Discussion leans defensive and focuses on balance-sheet or execution risk."
    return "Discussion is mixed, with both upside narrative and crowd-risk signals present."


def derive_factors(text: str) -> tuple[list[str], list[str], list[str]]:
    lowered = text.lower()
    bullish = [term for term in BULLISH_TERMS if term.lower() in lowered][:3]
    bearish = [term for term in BEARISH_TERMS if term.lower() in lowered][:3]
    risk = [term for term in RISK_TERMS if term.lower() in lowered][:3]
    return bullish, bearish, risk


def repeated_language_score(text: str) -> float:
    words = [token.strip(".,!?():;").lower() for token in text.split()]
    words = [word for word in words if len(word) > 3]
    if not words:
        return 0.0
    counts = Counter(words)
    repeated = sum(freq for freq in counts.values() if freq > 2)
    return min(repeated / max(len(words), 1), 1.0)


def analyze_text(text: str) -> dict[str, float | str | list[str]]:
    bullish_hits = _count_terms(text, BULLISH_TERMS)
    bearish_hits = _count_terms(text, BEARISH_TERMS)
    hype_hits = _count_terms(text, HYPE_TERMS)
    risk_hits = _count_terms(text, RISK_TERMS)

    bullish_score = _normalize_hits(bullish_hits)
    bearish_score = _normalize_hits(bearish_hits)
    hype_score = _normalize_hits(hype_hits)
    catalyst_score = min((bullish_score * 0.8) + (0.2 if bullish_hits else 0.0), 1.0)
    risk_language_score = min((bearish_score * 0.5) + (_normalize_hits(risk_hits) * 0.5), 1.0)

    sentiment_score = max(
        -1.0,
        min(1.0, (bullish_score * 0.9) - (bearish_score * 0.85) - (hype_score * 0.25)),
    )
    bullish_factors, bearish_factors, risk_flags = derive_factors(text)
    summary = summarize_text(text, sentiment_score, bullish_hits, bearish_hits)

    return {
        "sentiment_score": sentiment_score,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "hype_score": hype_score,
        "catalyst_score": catalyst_score,
        "risk_language_score": risk_language_score,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors,
        "risk_flags": risk_flags,
        "summary": summary,
        "repeated_language_score": repeated_language_score(text),
    }

