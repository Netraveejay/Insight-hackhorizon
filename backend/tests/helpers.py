"""Test factories and pipeline helpers."""

from __future__ import annotations

from datetime import datetime

from app.agents.clustering import ClusteringAgent
from app.agents.detection import DetectionAgent
from app.agents.ingestion import IngestionAgent
from app.agents.scoring import ScoringAgent
from app.agents.translation import TranslationAgent
from app.rules import RulesConfig
from app.schemas import RawFeedbackItem, ScoredItem, SourceCoverageEntry


def raw_feedback(**kwargs) -> RawFeedbackItem:
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


def score_raw(raw: RawFeedbackItem, rules: RulesConfig, run_id: str = "test") -> ScoredItem | None:
    ingested, _ = IngestionAgent().run(
        [raw],
        [SourceCoverageEntry(connector="test", status="ok", item_count=1, message="")],
        rules,
        run_id,
    )
    if not ingested:
        return None
    translated, _ = TranslationAgent().run_batch(ingested, rules, run_id, raw.week)
    return ScoringAgent().run(translated[0], rules)


def build_harbourview_p1_scenario(rules: RulesConfig) -> tuple[list, list, list[ScoredItem]]:
    """Multi-week Harbourview projection + staff KPI — returns clusters, current, all_scored."""
    weeks_data = {"2026-W24": 4, "2026-W25": 6, "2026-W26": 7}
    week_ts = {
        "2026-W24": datetime(2026, 6, 10, 19, 0),
        "2026-W25": datetime(2026, 6, 17, 19, 0),
        "2026-W26": datetime(2026, 6, 24, 19, 0),
    }
    all_scored: list[ScoredItem] = []

    for week, count in weeks_data.items():
        for i in range(count):
            s = score_raw(
                raw_feedback(
                    week=week,
                    ts=week_ts[week],
                    text=f"Projection dim and blurry {week} #{i}",
                ),
                rules,
            )
            if s:
                all_scored.append(s)
        if week in ("2026-W25", "2026-W26"):
            s = score_raw(
                raw_feedback(
                    source_type="staff",
                    channel="kpi_email",
                    week=week,
                    text="KPI flag: Projector lamp fault. Brightness below threshold.",
                    theme_hint="projection_quality",
                    sentiment_hint="negative",
                ),
                rules,
            )
            if s:
                all_scored.append(s)

    all_clusters = ClusteringAgent().run(all_scored, rules)
    current = [c for c in all_clusters if c.week == "2026-W26" and c.site_id == "harbourview"]
    return all_clusters, current, all_scored


def detect_harbourview_p1(rules: RulesConfig):
    all_clusters, current, all_scored = build_harbourview_p1_scenario(rules)
    hv = [c for c in current if c.theme == "projection_quality"]
    staff_clusters = [c for c in all_clusters if c.source_type in ("staff", "mixed")]
    detections = DetectionAgent().run(hv, all_clusters, staff_clusters, rules)
    det = next((d for d in detections if "harbourview" in d.cluster_id), None)
    return all_clusters, hv, det, all_scored
