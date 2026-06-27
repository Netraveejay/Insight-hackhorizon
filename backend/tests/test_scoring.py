import pytest
from datetime import datetime

from app.agents.clustering import ClusteringAgent
from app.agents.detection import DetectionAgent
from app.agents.ingestion import IngestionAgent
from app.agents.scoring import ScoringAgent
from app.agents.translation import TranslationAgent
from app.rules import load_rules
from app.schemas import Cluster, RawFeedbackItem, SourceCoverageEntry


@pytest.fixture
def rules():
    return load_rules()


def _raw(**kwargs) -> RawFeedbackItem:
    defaults = {
        "source_type": "guest",
        "channel": "csat",
        "site_id": "harbourview",
        "ts": datetime(2026, 6, 20, 19, 0),
        "week": "2026-W26",
        "rating": 2,
        "text": "The screen was very dim tonight, projector lamp seems faulty.",
        "theme_hint": "projection_quality",
        "sentiment_hint": "negative",
    }
    defaults.update(kwargs)
    return RawFeedbackItem(**defaults)


def _pipeline_item(raw: RawFeedbackItem, rules):
    ingested, _ = IngestionAgent().run(
        [raw], [SourceCoverageEntry(connector="test", status="ok")], rules, "test"
    )
    translated, _ = TranslationAgent().run_batch(ingested, rules, "test", raw.week)
    return ScoringAgent().run(translated[0], rules)


class TestScoring:
    def test_classifies_projection_theme(self, rules):
        scored = _pipeline_item(_raw(), rules)
        assert scored is not None
        assert "projection_quality" in scored.themes

    def test_non_controllable_deprioritised(self, rules):
        scored = _pipeline_item(
            _raw(text="Didn't like the film plot, ending was boring and too long.", theme_hint="non_controllable"),
            rules,
        )
        assert scored is not None
        assert scored.relevant is False
        assert scored.score == 0.0

    def test_disruption_high_urgency(self, rules):
        scored = _pipeline_item(
            _raw(
                source_type="staff",
                channel="disruption_notification",
                text="EVACUATION: Fire alarm triggered.",
            ),
            rules,
        )
        assert scored.urgency == "high"

    def test_spam_excluded(self, rules):
        items = [
            _raw(channel="public_review", site_id="southbank", text="Terrible cinema never coming back worst experience ever", rating=1)
            for _ in range(6)
        ]
        ingested, _ = IngestionAgent().run(
            items, [SourceCoverageEntry(connector="test", status="ok")], rules, "test"
        )
        assert any(i.is_spam for i in ingested)


class TestDetection:
    def _build_harbourview_scenario(self, rules):
        weeks_data = {"2026-W24": 4, "2026-W25": 6, "2026-W26": 7}
        all_scored = []
        week_ts = {"2026-W24": datetime(2026, 6, 10, 19, 0), "2026-W25": datetime(2026, 6, 17, 19, 0), "2026-W26": datetime(2026, 6, 24, 19, 0)}
        for week, count in weeks_data.items():
            for i in range(count):
                raw = _raw(week=week, ts=week_ts[week], text=f"Projection dim and blurry {week} #{i}")
                s = _pipeline_item(raw, rules)
                if s:
                    all_scored.append(s)
            if week in ("2026-W25", "2026-W26"):
                raw = _raw(
                    source_type="staff", channel="kpi_email", week=week,
                    text="KPI flag: Projector lamp fault. Brightness below threshold.",
                    theme_hint="projection_quality", sentiment_hint="negative",
                )
                s = _pipeline_item(raw, rules)
                if s:
                    all_scored.append(s)
        # Multilingual projection at Harbourview W26
        for text in ["屏幕太暗了，看不清楚电影画面", "La pantalla estaba muy oscura, difícil de ver"]:
            raw = _raw(week="2026-W26", ts=week_ts["2026-W26"], text=text, lang_hint="zh-cn")
            s = _pipeline_item(raw, rules)
            if s:
                all_scored.append(s)
        all_clusters = ClusteringAgent().run(all_scored, rules)
        current = [c for c in all_clusters if c.week == "2026-W26" and c.site_id == "harbourview"]
        return all_clusters, current

    def test_harbourview_p1_cross_source_compounding(self, rules):
        all_clusters, current = self._build_harbourview_scenario(rules)
        hv = [c for c in current if c.theme == "projection_quality"]
        assert len(hv) >= 1
        staff_clusters = [c for c in all_clusters if c.source_type in ("staff", "mixed")]
        detections = DetectionAgent().run(hv, all_clusters, staff_clusters, rules)
        det = next((d for d in detections if "harbourview" in d.cluster_id), None)
        assert det is not None
        assert det.compounding is not None
        assert det.cross_source is not None
        assert det.priority == "P1"
