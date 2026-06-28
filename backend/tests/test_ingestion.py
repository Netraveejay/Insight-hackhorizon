"""Unit tests — IngestionAgent."""

import pytest

from app.agents.ingestion import IngestionAgent
from app.schemas import SourceCoverageEntry

from tests.helpers import raw_feedback


@pytest.mark.unit
class TestIngestion:
    def test_pii_email_redacted(self, rules):
        raw = raw_feedback(text="Contact me at sarah.k@example.com about the dim screen.")
        ingested, _ = IngestionAgent().run(
            [raw], [SourceCoverageEntry(connector="test", status="ok")], rules, "run1"
        )
        assert ingested[0].pii_redacted is True
        assert "[EMAIL]" in ingested[0].text
        assert "example.com" not in ingested[0].text

    def test_duplicate_same_text_same_site_week(self, rules):
        raw = raw_feedback(text="Identical complaint text")
        items = [raw, raw_feedback(text="Identical complaint text")]
        ingested, _ = IngestionAgent().run(
            items, [SourceCoverageEntry(connector="test", status="ok")], rules, "run1"
        )
        assert ingested[0].is_duplicate is False
        assert ingested[1].is_duplicate is True

    def test_review_bomb_marked_spam(self, rules):
        text = "Terrible cinema never coming back worst experience ever"
        items = [
            raw_feedback(channel="public_review", site_id="southbank", text=text, rating=1)
            for _ in range(6)
        ]
        ingested, _ = IngestionAgent().run(
            items, [SourceCoverageEntry(connector="test", status="ok")], rules, "run1"
        )
        spam = [i for i in ingested if i.is_spam]
        assert len(spam) >= 4

    def test_stable_ids_for_same_input(self, rules):
        raw = raw_feedback()
        ingested, _ = IngestionAgent().run(
            [raw], [SourceCoverageEntry(connector="test", status="ok")], rules, "run1"
        )
        again, _ = IngestionAgent().run(
            [raw], [SourceCoverageEntry(connector="test", status="ok")], rules, "run2"
        )
        assert ingested[0].id == again[0].id
