"""Integration tests — full Orchestrator pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from datetime import datetime

from app.models import DetectionRow, RunRow
from app.orchestrator import Orchestrator
from app.schemas import RawFeedbackItem, SourceCoverageEntry

from tests.helpers import build_harbourview_p1_scenario, raw_feedback

WEEK_TS = {
    "2026-W24": datetime(2026, 6, 10, 19, 0),
    "2026-W25": datetime(2026, 6, 17, 19, 0),
    "2026-W26": datetime(2026, 6, 24, 19, 0),
}


class _ListConnector:
    name = "test"

    def __init__(self, items: list[RawFeedbackItem]):
        self._items = items

    def fetch(self, week=None):
        return self._items, SourceCoverageEntry(
            connector=self.name, status="ok", item_count=len(self._items), message="test"
        )


@pytest.mark.integration
class TestOrchestrator:
    def test_pipeline_persists_root_cause_and_sla_on_p1(self, db, rules):
        """Run a minimal pipeline and verify detection payload includes enrichment."""
        raw_items = [
            raw_feedback(text=f"Screen very dim session {i}") for i in range(8)
        ]
        raw_items.append(
            raw_feedback(
                source_type="staff",
                channel="kpi_email",
                text="KPI: Auditorium 3 lamp hours exceeded threshold.",
            )
        )
        connector = _ListConnector(raw_items)

        with patch("app.orchestrator.load_connectors", return_value=[connector]):
            result = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")

        assert result.week == "2026-W26"
        assert result.items_scored > 0
        assert result.detections >= 0

        run = db.query(RunRow).filter(RunRow.id == result.run_id).first()
        assert run is not None
        assert run.status == "completed"

        p1_rows = db.query(DetectionRow).filter(
            DetectionRow.run_id == result.run_id, DetectionRow.priority == "P1"
        ).all()
        for row in p1_rows:
            payload = row.payload or {}
            assert payload.get("root_cause"), f"missing root_cause on {row.cluster_id}"
            assert payload.get("sla"), f"missing sla on {row.cluster_id}"

    def test_pipeline_clears_previous_artifacts_on_rerun(self, db, rules):
        raw_items = [raw_feedback(text="Queue was very long at peak")]
        connector = _ListConnector(raw_items)

        with patch("app.orchestrator.load_connectors", return_value=[connector]):
            first = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")
            second = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")

        assert first.run_id != second.run_id
        runs = db.query(RunRow).filter(RunRow.week == "2026-W26").count()
        assert runs == 2

    def test_explanation_attached_to_run_stats(self, db, rules):
        _, _, all_scored = build_harbourview_p1_scenario(rules)
        assert len(all_scored) > 0

        # Use harbourview scenario via many raw projection complaints across weeks
        raw_items: list[RawFeedbackItem] = []
        for week, n in {"2026-W24": 4, "2026-W25": 6, "2026-W26": 7}.items():
            for i in range(n):
                raw_items.append(
                    raw_feedback(
                        week=week,
                        ts=WEEK_TS[week],
                        text=f"Projection dim blurry {week} #{i}",
                    )
                )
            if week in ("2026-W25", "2026-W26"):
                raw_items.append(
                    raw_feedback(
                        source_type="staff",
                        channel="kpi_email",
                        week=week,
                        ts=WEEK_TS[week],
                        text=f"KPI: lamp fault auditorium 3 ({week})",
                    )
                )

        with patch("app.orchestrator.load_connectors", return_value=[_ListConnector(raw_items)]):
            result = Orchestrator(db).run_pipeline(week="2026-W26", cadence="test")

        run = db.query(RunRow).filter(RunRow.id == result.run_id).first()
        assert run.stats.get("explanation")
        assert result.explanation is not None
        assert len(result.explanation["steps"]) == 7
