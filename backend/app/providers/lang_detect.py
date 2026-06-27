"""Offline language detection — no API key required."""

from __future__ import annotations

DETECTOR_VERSION = "langdetect-v1"


def detect_language(text: str) -> tuple[str, float]:
    """
    Returns (iso_code, confidence). Defaults to ('en', 1.0) on empty or failure.
    """
    if not text or not text.strip():
        return "en", 1.0
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        results = detect_langs(text)
        if results:
            top = results[0]
            return top.lang, float(top.prob)
    except Exception:
        pass
    return "en", 0.5
