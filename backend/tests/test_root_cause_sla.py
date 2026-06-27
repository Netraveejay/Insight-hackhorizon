from datetime import datetime, timedelta

import pytest

from app.agents.root_cause import RootCauseAgent
from app.rules import load_rules
from app.sla import compute_sla
from app.schemas import Cluster, Detection


@pytest.fixture
def rules():
    return load_rules()


def test_compute_sla_on_track(rules):
    triggered = datetime.utcnow()
    sla = compute_sla("P1", triggered, rules.sla)
    assert sla["status"] == "on_track"
    assert sla["response_hours"] == 4
    assert sla["resolution_hours"] == 48
    assert "On track" in sla["label"]


def test_compute_sla_at_risk(rules):
    triggered = datetime.utcnow() - timedelta(hours=5)
    sla = compute_sla("P1", triggered, rules.sla)
    assert sla["status"] == "at_risk"
    assert sla["phase"] == "resolution"


def test_compute_sla_breached(rules):
    triggered = datetime.utcnow() - timedelta(hours=72)
    sla = compute_sla("P1", triggered, rules.sla)
    assert sla["status"] == "breached"


def test_root_cause_projection_keywords(rules):
    cluster = Cluster(
        cluster_id="harbourview-projection_quality-2026-W26",
        site_id="harbourview",
        theme="projection_quality",
        week="2026-W26",
        volume=5,
        neg=4,
        pos=1,
        net_sentiment=-0.6,
        item_ids=["a", "b"],
        confidence_band="high",
        source_type="mixed",
    )
    detection = Detection(
        cluster_id=cluster.cluster_id,
        spike=None,
        compounding={"weeks": 3},
        cross_source={"staff_ref": "staff", "staff_neg": 2},
        priority="P1",
    )
    from app.schemas import ScoredItem

    items = [
        ScoredItem(
            id="a",
            source_type="guest",
            channel="csat",
            site_id="harbourview",
            ts=datetime(2026, 6, 20),
            week="2026-W26",
            rating=2,
            channel_weight=1.0,
            is_duplicate=False,
            is_spam=False,
            pii_redacted=False,
            text="The screen was very dim tonight, projector lamp seems faulty.",
            original_text="The screen was very dim tonight, projector lamp seems faulty.",
            original_language="en",
            translated=False,
            translation_provider="none",
            translation_confidence="high",
            themes=["projection_quality"],
            primary_theme="projection_quality",
            sentiment={"projection_quality": "negative"},
            relevant=True,
            urgency="high",
            score=0.8,
            rules_version="1.4",
        )
    ]
    rc = RootCauseAgent().run(cluster, detection, items, rules)
    assert rc["category"] == "Equipment — projection"
    assert "lamp" in rc["summary"].lower() or "Projector" in rc["summary"]
    assert rc["confidence"] == "high"
    assert any("weeks" in f.lower() for f in rc["contributing_factors"])
