"""Unit tests — OutputAgent overview and SLA summary."""

import pytest

from app.agents.output import OutputAgent
from app.schemas import Cluster, Detection, Insight

from tests.helpers import detect_harbourview_p1


@pytest.mark.unit
class TestOutput:
    def test_overview_includes_sla_summary(self, rules):
        all_clusters, hv, det, _ = detect_harbourview_p1(rules)
        cluster = hv[0]
        det = det.model_copy(
            update={
                "root_cause": {"summary": "Projector lamp issue"},
                "sla": {"status": "on_track", "label": "On track — acknowledge within 4h"},
            }
        )
        insights = [
            Insight(
                cluster_id=cluster.cluster_id,
                insight="Inspect projection within 48 hours.",
                evidence_sample=["a"],
                owner_suggested="Technical Operations",
                rules_version=rules.version,
            )
        ]
        overview = OutputAgent().render_overview([], [cluster], [det], insights, "2026-W26")
        assert overview["sla_summary"]["on_track"] == 1
        assert overview["hero_issue"]["root_cause_summary"] == "Projector lamp issue"
        assert overview["hero_issue"]["sla_status"] == "on_track"
