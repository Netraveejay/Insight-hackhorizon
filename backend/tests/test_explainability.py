from datetime import datetime

from app.agents.explainability import ExplainabilityAgent
from app.schemas import Cluster, Detection, IngestedItem, Insight, ScoredItem, TranslatedItem


def _ingested(**kw) -> IngestedItem:
    base = dict(
        id="x1",
        source_type="guest",
        channel="public_review",
        site_id="harbourview",
        ts=datetime(2026, 6, 25, 12, 0, 0),
        week="2026-W26",
        rating=2,
        text="Screen was blurry",
        channel_weight=1.0,
        is_duplicate=False,
        is_spam=False,
        pii_redacted=False,
    )
    base.update(kw)
    return IngestedItem(**base)


def _translated(**kw) -> TranslatedItem:
    item = _ingested(**kw)
    return TranslatedItem(
        **item.model_dump(),
        original_text=item.text,
        original_language=kw.get("original_language", "en"),
        translated=kw.get("translated", False),
        translation_provider="passthrough",
        translation_confidence="high",
    )


def _scored(**kw) -> ScoredItem:
    item = _translated(**kw)
    return ScoredItem(
        **item.model_dump(),
        themes=["projection_quality"],
        primary_theme="projection_quality",
        sentiment={"projection_quality": "negative"},
        urgency="normal",
        relevant=True,
        score=0.8,
        rules_version="1.3",
    )


class TestExplainability:
    def test_hero_narrative_for_harbourview(self):
        cluster = Cluster(
            cluster_id="harbourview__projection_quality__2026-W26",
            site_id="harbourview",
            theme="projection_quality",
            week="2026-W26",
            volume=8,
            neg=6,
            pos=0,
            net_sentiment=-1.0,
            confidence_band="high",
            item_ids=["a", "b"],
            source_type="mixed",
        )
        detection = Detection(
            cluster_id=cluster.cluster_id,
            compounding={"weeks": 3, "first_seen": "2026-W24"},
            cross_source={"staff_ref": "staff", "staff_neg": 2},
            priority="P1",
        )
        insight = Insight(
            cluster_id=cluster.cluster_id,
            insight="Inspect projection at Harbourview within 48 hours.",
            evidence_sample=["a"],
            owner_suggested="Technical Operations",
            rules_version="1.3",
        )
        agent = ExplainabilityAgent()
        result = agent.run(
            week="2026-W26",
            run_id="run1",
            rules_version="1.3",
            cadence="manual",
            ingested=[_ingested()],
            translated=[_translated()],
            scored=[_scored()],
            current_clusters=[cluster],
            detections=[detection],
            insights=[insight],
            alerts_count=2,
            hero_cluster_id=cluster.cluster_id,
        )
        assert result.hero is not None
        assert result.hero.site_name == "Harbourview"
        assert "P1" in result.headline or "critical" in result.headline.lower()
        assert any("Cross-source" in r for r in result.hero.reasons)
        assert len(result.steps) == 7
