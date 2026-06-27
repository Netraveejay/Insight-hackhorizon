from __future__ import annotations

import re

from app.rules import RulesConfig
from app.schemas import IngestedItem, ScoredItem, TranslatedItem


SENTIMENT_VALUES = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}


class ScoringAgent:
    """Deterministic, rules-driven scoring — no LLM."""

    METHOD_VERSION = "lexicon-v1"

    def run(self, item: TranslatedItem, rules: RulesConfig) -> ScoredItem | None:
        if item.is_spam or item.is_duplicate:
            return None

        text_lower = item.text.lower()
        themes = self._classify_themes(text_lower, rules)
        if not themes:
            themes = ["staff_service"]  # default bucket for unclassified

        primary_theme = themes[0]
        if item.theme_hint and item.theme_hint in rules.themes:
            primary_theme = item.theme_hint
            if item.theme_hint not in themes:
                themes = [item.theme_hint] + themes

        sentiment = {t: self._classify_sentiment(text_lower, t, rules, item) for t in themes}
        urgency = self._classify_urgency(text_lower, item, rules)
        relevant = self._check_relevance(text_lower, rules)

        if not relevant:
            score = 0.0
        else:
            sent_val = SENTIMENT_VALUES.get(sentiment.get(primary_theme, "neutral"), 0.0)
            rating_factor = self._rating_factor(item.rating, sent_val)
            site_weight = rules.site_size_weight(item.site_id)
            score = abs(sent_val) * item.channel_weight * site_weight * rating_factor
            if sent_val < 0:
                score = -score  # negative scores for negative sentiment

        return ScoredItem(
            **item.model_dump(),
            themes=themes,
            primary_theme=primary_theme,
            sentiment=sentiment,
            urgency=urgency,
            relevant=relevant,
            score=round(score, 4),
            rules_version=rules.version,
        )

    def _classify_themes(self, text: str, rules: RulesConfig) -> list[str]:
        scores: dict[str, int] = {}
        for theme, keywords in rules.themes.items():
            count = sum(1 for kw in keywords if kw.lower() in text)
            if count:
                scores[theme] = count
        if not scores:
            return []
        return sorted(scores, key=lambda t: (-scores[t], t))

    def _classify_sentiment(
        self, text: str, theme: str, rules: RulesConfig, item: TranslatedItem
    ) -> str:
        if item.sentiment_hint in ("positive", "negative", "neutral"):
            return item.sentiment_hint  # type: ignore[return-value]
        if item.rating is not None:
            if item.rating >= 4:
                return "positive"
            if item.rating <= 2:
                return "negative"
        pos_hits = sum(1 for w in rules.sentiment.get("positive", []) if w.lower() in text)
        neg_hits = sum(1 for w in rules.sentiment.get("negative", []) if w.lower() in text)
        if neg_hits > pos_hits:
            return "negative"
        if pos_hits > neg_hits:
            return "positive"
        return "neutral"

    def _classify_urgency(self, text: str, item: TranslatedItem, rules: RulesConfig) -> str:
        if item.channel == "disruption_notification":
            return "high"
        for kw in rules.high_urgency_keywords:
            if kw.lower() in text:
                return "high"
        return "normal"

    def _check_relevance(self, text: str, rules: RulesConfig) -> bool:
        for phrase in rules.relevance_filter.get("non_controllable", []):
            if phrase.lower() in text:
                return False
        return True

    def _rating_factor(self, rating: int | None, sentiment_val: float) -> float:
        if rating is None:
            return 1.0
        if sentiment_val < 0:
            return max(0.5, (6 - rating) / 4)
        if sentiment_val > 0:
            return max(0.5, rating / 5)
        return 1.0
