from __future__ import annotations

from collections import defaultdict

from app.providers.lang_detect import DETECTOR_VERSION, detect_language
from app.providers.translator import TRANSLATOR_VERSION, get_translator
from app.rules import RulesConfig
from app.schemas import IngestedItem, LanguageStat, LanguageStatsReport, TranslatedItem


class TranslationAgent:
    """Detect language and translate to English. Original always retained."""

    def run_batch(
        self, items: list[IngestedItem], rules: RulesConfig, run_id: str, week: str
    ) -> tuple[list[TranslatedItem], LanguageStatsReport]:
        translator = get_translator()
        target = rules.translation.get("target_language", "en")
        low_threshold = float(rules.translation.get("low_confidence_flag_below", 0.6))

        translated_items: list[TranslatedItem] = []
        lang_counts: dict[str, int] = defaultdict(int)
        lang_translated: dict[str, int] = defaultdict(int)

        for item in items:
            original = item.text
            lang, detect_conf = detect_language(original)
            lang_base = lang.split("-")[0].lower()

            if lang_base == target:
                text_en = original
                t_out = type(
                    "T",
                    (),
                    {
                        "text_en": original,
                        "provider": "passthrough",
                        "confidence": "high",
                        "was_translated": False,
                    },
                )()
            else:
                t_out = translator.translate(original, lang_base, target)
                text_en = t_out.text_en

            trans_conf: str = t_out.confidence
            if not t_out.was_translated and lang_base != target:
                if detect_conf < low_threshold:
                    trans_conf = "low"
                else:
                    trans_conf = "low"

            lang_counts[lang_base] += 1
            if t_out.was_translated:
                lang_translated[lang_base] += 1

            translated_items.append(
                TranslatedItem(
                    **item.model_dump(exclude={"text"}),
                    original_text=original,
                    original_language=lang_base,
                    translated=t_out.was_translated,
                    text=text_en,
                    translation_provider=t_out.provider,
                    translation_confidence=trans_conf,  # type: ignore[arg-type]
                )
            )

        stats = LanguageStatsReport(
            run_id=run_id,
            week=week,
            languages=[
                LanguageStat(language=lang, count=c, translated_count=lang_translated.get(lang, 0))
                for lang, c in sorted(lang_counts.items(), key=lambda x: -x[1])
            ],
            total_items=len(items),
        )
        return translated_items, stats

    @property
    def versions(self) -> dict[str, str]:
        return {"detector": DETECTOR_VERSION, "translator": TRANSLATOR_VERSION}
