from __future__ import annotations

import re
from functools import lru_cache

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")

BASIC_TRANSLATIONS = {
    "苹果回购继续，估值还是不贵，AAPL 这波像是慢牛继续。": "Apple buybacks continue and the valuation still does not look expensive; AAPL still looks like a steady bull trend.",
    "AMD 业绩超预期，数据中心增长加速，感觉还有突破空间。": "AMD beat expectations, data-center growth is accelerating, and there still looks to be room for a breakout.",
    "SOFI 高位接盘风险太大，盈利质量一般，还要小心稀释。": "SOFI looks risky to chase at these levels, earnings quality is average, and dilution risk still matters.",
    "特斯拉交付压力还在，TSLA 这次反弹更像情绪修复。": "Tesla still faces delivery pressure and this TSLA bounce looks more like sentiment repair than a durable fundamental move.",
    "英伟达太热了，NVDA 像下一段挤压前的最后疯狂。": "NVIDIA looks overheated; NVDA feels like the last burst before the next squeeze unwinds.",
}


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    if CJK_PATTERN.search(text):
        return "zh"
    return "en"


@lru_cache(maxsize=1)
def _get_openai_client(api_key: str | None):
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def translate_text(
    text: str,
    source_language: str,
    target_language: str = "en",
    *,
    api_key: str | None = None,
    enable_translation: bool = True,
) -> str | None:
    if not text or source_language == target_language:
        return text
    if source_language != "zh":
        return text
    if text in BASIC_TRANSLATIONS:
        return BASIC_TRANSLATIONS[text]
    if not enable_translation:
        return None

    client = _get_openai_client(api_key)
    if client is None:
        return None

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                "Translate the following Chinese finance discussion to concise English. "
                "Preserve the stock ticker.\n\n"
                f"{text}"
            ),
        )
        return response.output_text.strip() or None
    except Exception:
        return None

