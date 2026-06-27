"""Tests for TranslationAgent and multilingual ingestion."""

from datetime import datetime

import pytest

from app.agents.ingestion import IngestionAgent
from app.agents.scoring import ScoringAgent
from app.agents.translation import TranslationAgent
from app.rules import load_rules
from app.schemas import RawFeedbackItem, SourceCoverageEntry


@pytest.fixture
def rules():
    return load_rules()


def _run(raw: RawFeedbackItem, rules):
    ingested, _ = IngestionAgent().run(
        [raw], [SourceCoverageEntry(connector="test", status="ok", item_count=1)], rules, "test"
    )
    translated, stats = TranslationAgent().run_batch(ingested, rules, "test", raw.week)
    return translated[0], stats


class TestMultilingual:
    def test_chinese_translated_to_english(self, rules):
        raw = RawFeedbackItem(
            source_type="guest", channel="public_review", site_id="harbourview",
            ts=datetime(2026, 6, 24, 19, 0), week="2026-W26", rating=2,
            text="屏幕太暗了，看不清楚电影画面", lang_hint="zh-cn",
        )
        item, _ = _run(raw, rules)
        assert item.translated is True
        assert item.original_language in ("zh", "zh-cn")
        assert "dim" in item.text.lower() or "screen" in item.text.lower()

    def test_english_passthrough(self, rules):
        raw = RawFeedbackItem(
            source_type="guest", channel="csat", site_id="harbourview",
            ts=datetime(2026, 6, 24, 19, 0), week="2026-W26", rating=4,
            text="The screen was very dim tonight.", lang_hint="en",
        )
        item, _ = _run(raw, rules)
        assert item.translated is False
        assert item.original_language == "en"

    def test_translated_scores_f_and_b(self, rules):
        raw = RawFeedbackItem(
            source_type="guest", channel="public_review", site_id="cityplaza",
            ts=datetime(2026, 6, 24, 19, 0), week="2026-W26", rating=2,
            text="爆米花是温的，而且太贵了", theme_hint="f_and_b", lang_hint="zh-cn",
        )
        item, _ = _run(raw, rules)
        scored = ScoringAgent().run(item, rules)
        assert scored is not None
        assert "f_and_b" in scored.themes or scored.primary_theme == "f_and_b"

    def test_language_stats_accumulated(self, rules):
        raw = RawFeedbackItem(
            source_type="guest", channel="public_review", site_id="harbourview",
            ts=datetime(2026, 6, 24, 19, 0), week="2026-W26", rating=2,
            text="La pantalla estaba muy oscura, difícil de ver", lang_hint="es",
        )
        _, stats = _run(raw, rules)
        assert stats.total_items == 1
        assert len(stats.languages) >= 1
