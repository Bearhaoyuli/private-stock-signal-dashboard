from app.core.config import get_settings
from app.services.detect_translate_language import detect_language, translate_text


if __name__ == "__main__":
    settings = get_settings()
    sample = "AMD 业绩超预期，数据中心增长加速，感觉还有突破空间。"
    language = detect_language(sample)
    translated = translate_text(
        sample,
        language,
        api_key=settings.openai_api_key,
        enable_translation=settings.enable_translation,
    )
    print({"language": language, "translated": translated})

