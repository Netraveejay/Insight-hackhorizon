"""Tests for theatre leaderboard scoring."""

from datetime import datetime

from app.leaderboard import build_leaderboard, prior_week
from app.schemas import Cluster, Detection, ScoredItem


def _cluster(site_id: str, theme: str, week: str, neg: int = 0, pos: int = 0) -> Cluster:
    cid = f"{site_id}__{theme}__{week}"
    return Cluster(
        cluster_id=cid,
        site_id=site_id,
        theme=theme,
        week=week,
        volume=neg + pos,
        neg=neg,
        pos=pos,
        net_sentiment=pos - neg,
        confidence_band="high",
        item_ids=[],
    )


def _detection(
    cluster: Cluster,
    priority: str = "P2",
    compounding: bool = False,
    sla_status: str = "on_track",
) -> Detection:
    return Detection(
        cluster_id=cluster.cluster_id,
        spike=None,
        compounding={"weeks": 3} if compounding else None,
        cross_source=None,
        priority=priority,
        root_cause={"summary": "test"},
        sla={"status": sla_status, "label": sla_status},
    )


def _scored(site_id: str, rating: int = 5) -> ScoredItem:
    return ScoredItem(
        id=f"{site_id}-1",
        source_type="guest",
        channel="csat",
        site_id=site_id,
        ts=datetime(2026, 6, 20, 12, 0, 0),
        week="2026-W26",
        rating=rating,
        channel_weight=1.0,
        is_duplicate=False,
        is_spam=False,
        pii_redacted=False,
        original_text="Great",
        original_language="en",
        translated=False,
        text="Great",
        translation_provider="none",
        translation_confidence="high",
        themes=["staff_service"],
        primary_theme="staff_service",
        sentiment={"staff_service": "positive"},
        urgency="normal",
        relevant=True,
        score=1.0,
        rules_version="1.3",
    )


def test_prior_week():
    assert prior_week("2026-W26") == "2026-W25"
    assert prior_week("2026-W01") is None


def test_leaderboard_ranks_better_theatre_higher():
    week = "2026-W26"
    pw = "2026-W25"

    good = _cluster("westgate", "staff_service", week, neg=1, pos=5)
    bad = _cluster("harbourview", "projection_quality", week, neg=8, pos=0)
    prior_bad = _cluster("harbourview", "projection_quality", pw, neg=10, pos=0)

    clusters = [good, bad]
    prior = [prior_bad]
    detections = [
        _detection(good, priority="P3", compounding=False, sla_status="on_track"),
        _detection(bad, priority="P1", compounding=True, sla_status="breached"),
    ]
    scored = [_scored("westgate", 5), _scored("harbourview", 2)]

    result = build_leaderboard(week, clusters, prior, detections, scored)
    assert result["entries"]
    lakeshore = next(e for e in result["entries"] if e["theatre_id"] == "lakeshore")
    metro = next(e for e in result["entries"] if e["theatre_id"] == "metro-cinemas")
    assert lakeshore["efficiency_score"] > metro["efficiency_score"]
    westgate = next(s for s in lakeshore["sites"] if s["site_id"] == "westgate")
    harbourview = next(s for s in metro["sites"] if s["site_id"] == "harbourview")
    assert westgate["efficiency_score"] > harbourview["efficiency_score"]
