"""Unit tests — ClusteringAgent."""

import pytest

from app.agents.clustering import ClusteringAgent

from tests.helpers import raw_feedback, score_raw


@pytest.mark.unit
class TestClustering:
    def test_groups_by_site_theme_week(self, rules):
        items = [
            score_raw(raw_feedback(site_id="harbourview", week="2026-W26"), rules),
            score_raw(raw_feedback(site_id="northgate", week="2026-W26", theme_hint="ticketing_queue"), rules),
        ]
        items = [i for i in items if i]
        clusters = ClusteringAgent().run(items, rules)
        assert len(clusters) == 2
        keys = {(c.site_id, c.theme, c.week) for c in clusters}
        assert ("harbourview", "projection_quality", "2026-W26") in keys

    def test_mixed_source_type_when_guest_and_staff(self, rules):
        guest = score_raw(raw_feedback(source_type="guest", channel="csat"), rules)
        staff = score_raw(
            raw_feedback(
                source_type="staff",
                channel="kpi_email",
                text="KPI: projector lamp fault in auditorium 3",
            ),
            rules,
        )
        clusters = ClusteringAgent().run([guest, staff], rules)
        cluster = next(c for c in clusters if c.site_id == "harbourview")
        assert cluster.source_type == "mixed"
        assert len(cluster.item_ids) == 2

    def test_skips_non_relevant_items(self, rules):
        scored = score_raw(
            raw_feedback(text="Didn't like the film plot, boring storyline.", theme_hint="non_controllable"),
            rules,
        )
        clusters = ClusteringAgent().run([scored], rules)
        assert clusters == []
