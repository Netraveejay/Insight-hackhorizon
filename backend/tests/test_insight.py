"""Unit tests — InsightAgent (template path, no OpenAI)."""

import pytest

from app.agents.insight import InsightAgent
from app.schemas import Cluster, Detection

from tests.helpers import detect_harbourview_p1


@pytest.mark.unit
class TestInsight:
    def test_template_draft_without_openai(self, rules, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        from app.config import get_settings

        get_settings.cache_clear()

        _, hv, det, _ = detect_harbourview_p1(rules)
        cluster = hv[0]
        agent = InsightAgent()
        insight = agent.run(cluster, det, [], rules.version)

        assert insight.draft_source == "template"
        assert insight.status == "draft_recommendation"
        assert "Harbourview" in insight.insight or "harbourview" in insight.insight.lower()
        assert insight.owner_suggested == "Technical Operations"
        assert len(insight.insight.split()) <= 60

    def test_owner_map_ticketing(self, rules):
        cluster = Cluster(
            cluster_id="northgate__ticketing_queue__2026-W26",
            site_id="northgate",
            theme="ticketing_queue",
            week="2026-W26",
            volume=5,
            neg=4,
            pos=0,
            net_sentiment=-1.0,
            confidence_band="medium",
            item_ids=["a"],
            source_type="guest",
        )
        det = Detection(cluster_id=cluster.cluster_id, priority="P2")
        insight = InsightAgent().run(cluster, det, [], rules.version)
        assert insight.owner_suggested == "Front of House Manager"
