from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from app.rules import RulesConfig
from app.schemas import IngestedItem, RawFeedbackItem, SourceCoverageEntry, SourceCoverageReport


PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b(?:\+?61|0)[2-478](?:[ -]?[0-9]){8}\b"), "[PHONE]"),
    (re.compile(r"\b0[2-478](?:[ -]?[0-9]){8}\b"), "[PHONE]"),
    (re.compile(r"\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+\b"), "[NAME]"),
]


class IngestionAgent:
    """Deterministic ingestion — normalise, dedupe, spam filter, PII redact."""

    def run(
        self,
        raw_items: list[RawFeedbackItem],
        coverage_entries: list[SourceCoverageEntry],
        rules: RulesConfig,
        run_id: str,
    ) -> tuple[list[IngestedItem], SourceCoverageReport]:
        seen_text_site: set[str] = set()
        ingested: list[IngestedItem] = []
        spam_keys = self._detect_review_bombs(raw_items)

        for item in raw_items:
            text_key = f"{item.site_id}::{item.week}::{item.text.strip().lower()}"
            is_duplicate = text_key in seen_text_site
            seen_text_site.add(text_key)

            text, pii_redacted = self._redact_pii(item.text)
            is_spam = f"{item.site_id}::{item.week}" in spam_keys and item.channel == "public_review"

            stable_id = hashlib.sha256(
                f"{item.site_id}:{item.channel}:{item.ts.isoformat()}:{item.text[:80]}".encode()
            ).hexdigest()[:16]

            ingested.append(
                IngestedItem(
                    id=stable_id,
                    source_type=item.source_type,
                    channel=item.channel,
                    site_id=item.site_id,
                    ts=item.ts,
                    week=item.week,
                    rating=item.rating,
                    theme_hint=item.theme_hint,
                    sentiment_hint=item.sentiment_hint,
                    lang_hint=item.lang_hint,
                    text=text,
                    channel_weight=rules.channel_weight_for(item.channel, item.source_type),
                    is_duplicate=is_duplicate,
                    is_spam=is_spam,
                    pii_redacted=pii_redacted,
                )
            )

        return ingested, SourceCoverageReport(run_id=run_id, entries=coverage_entries)

    def _redact_pii(self, text: str) -> tuple[str, bool]:
        redacted = False
        result = text
        for pattern, replacement in PII_PATTERNS:
            new_result, n = pattern.subn(replacement, result)
            if n:
                redacted = True
                result = new_result
        return result, redacted

    def _detect_review_bombs(self, items: list[RawFeedbackItem]) -> set[str]:
        buckets: dict[str, list[str]] = defaultdict(list)
        for item in items:
            if item.channel == "public_review" and item.rating is not None and item.rating <= 2:
                key = f"{item.site_id}::{item.week}"
                norm = re.sub(r"\s+", " ", item.text.strip().lower())[:60]
                buckets[key].append(norm)
        spam_keys: set[str] = set()
        for key, texts in buckets.items():
            if len(texts) >= 5:
                from collections import Counter

                if Counter(texts).most_common(1)[0][1] >= 4:
                    spam_keys.add(key)
        return spam_keys
