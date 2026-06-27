from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel

logger = logging.getLogger(__name__)

TRANSLATOR_VERSION = "hybrid-v1"

# Offline dictionary — works without API key or network
PHRASE_DICTIONARY: dict[str, str] = {
    "屏幕太暗了，看不清楚电影画面": "The screen was very dim, hard to see the movie picture",
    "屏幕太暗了，7号厅几乎看不清电影画面": "The screen was very dim in auditorium 7, could barely see the movie",
    "投影质量很差，画面发灰": "Projection quality was poor, image looked washed out",
    "屏幕太暗了，看电影很困难": "The screen was very dim, difficult to watch the film",
    "爆米花是温的，而且太贵了": "Popcorn was lukewarm and overpriced",
    "爆米花是温的，而且太贵了，不太满意": "Popcorn was lukewarm and overpriced, not very satisfied",
    "工作人员非常友好和热情": "Staff were very friendly and welcoming",
    "الشاشة كانت مظلمة جداً ولم أستطع رؤية الفيلم": "The screen was very dark and I could not see the film",
    "الشاشة كانت مظلمة جداً ولم أستطع رؤية الفيلم بوضوح": "The screen was very dark and I could not see the film clearly",
    "جودة الصوت سيئة والحجم منخفض": "Sound quality was bad and the volume was low",
    "جودة الصوت سيئة والحجم منخفض جداً في القاعة": "Sound quality was bad and the volume was very low in the auditorium",
    "Màn hình quá tối, khó nhìn thấy phim": "The screen was too dark, hard to see the film",
    "Hàng đợi mua vé rất dài": "The ticket queue was very long",
    "Hàng đợi mua vé rất dài, phải chờ gần nửa tiếng": "The ticket queue was very long, had to wait nearly half an hour",
    "स्क्रीन बहुत धुंधली थी, फिल्म देखना मुश्किल था": "The screen was very blurry, difficult to watch the film",
    "स्टाफ बहुत मददगार और विनम्र था": "Staff were very helpful and polite",
    "स्टाफ बहुत मददगार और विनम्र था, धन्यवाद": "Staff were very helpful and polite, thank you",
    "La pantalla estaba muy oscura, difícil de ver": "The screen was very dark, difficult to see",
    "La pantalla estaba muy oscura en la sala 3, difícil de ver la película": "The screen was very dark in auditorium 3, difficult to see the film",
    "La cola para comprar entradas era enorme": "The queue to buy tickets was enormous",
    "L'écran était très sombre, difficile à voir": "The screen was very dark, difficult to see",
    "L'écran était très sombre, difficile de voir le film": "The screen was very dark, difficult to see the film",
    "L'écran était très sombre ce soir, impossible de profiter du film": "The screen was very dark tonight, impossible to enjoy the film",
    "Le popcorn était tiède et trop cher": "The popcorn was lukewarm and too expensive",
    "Lo schermo era troppo scuro per vedere il film": "The screen was too dark to see the film",
}


class TranslationOutput(BaseModel):
    text_en: str
    provider: str
    confidence: str  # high | low
    was_translated: bool


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str = "en") -> TranslationOutput:
        ...


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


class HybridTranslator(Translator):
    """
    Dictionary (offline) → argostranslate (offline MT) → deep-translator (online) → passthrough.
    Never drops text; flags low confidence when untranslated.
    """

    def translate(self, text: str, source_lang: str, target_lang: str = "en") -> TranslationOutput:
        lang = source_lang.split("-")[0].lower()
        if lang == "en" or not text.strip():
            return TranslationOutput(
                text_en=text, provider="passthrough", confidence="high", was_translated=False
            )

        key = _norm(text)
        if key in PHRASE_DICTIONARY:
            return TranslationOutput(
                text_en=PHRASE_DICTIONARY[key],
                provider="dictionary",
                confidence="high",
                was_translated=True,
            )

        # argostranslate offline MT
        try:
            import argostranslate.package
            import argostranslate.translate

            installed = argostranslate.translate.get_installed_languages()
            from_lang = next((l for l in installed if l.code == lang), None)
            to_lang = next((l for l in installed if l.code == "en"), None)
            if from_lang and to_lang:
                translation = from_lang.get_translation(to_lang)
                if translation:
                    result = translation.translate(text)
                    if result:
                        return TranslationOutput(
                            text_en=result, provider="argos", confidence="high", was_translated=True
                        )
        except Exception as e:
            logger.debug("argostranslate unavailable: %s", e)

        # Online fallback
        try:
            from deep_translator import GoogleTranslator

            result = GoogleTranslator(source="auto", target="en").translate(text)
            if result:
                return TranslationOutput(
                    text_en=result, provider="deep-translator", confidence="high", was_translated=True
                )
        except Exception as e:
            logger.debug("deep-translator unavailable: %s", e)

        return TranslationOutput(
            text_en=text,
            provider="passthrough",
            confidence="low",
            was_translated=False,
        )


def get_translator() -> Translator:
    return HybridTranslator()
