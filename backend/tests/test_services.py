"""Unit/integration tests — services layer enrichment."""

from datetime import datetime

import pytest

from app.models import ClusterRow, DetectionRow, FeedbackScored, RunRow
from app.services import detection_for_cluster, detections_for_week, enrich_detection

from tests.helpers import detect_harbourview_p1


@pytest.mark.integration
class TestServicesEnrichment:
    def _seed_run_with_detection(self, db, rules):
        _, hv, det, all_scored = detect_harbourview_p1(rules)
        cluster = hv[0]
        run_id = "test-run-enrich"
        week = "2026-W26"
        scored_by_id = {s.id: s for s in all_scored}

        db.add(
            RunRow(
                id=run_id,
                cadence="test",
                week=week,
                rules_version=rules.version,
                status="completed",
                started_at=datetime.utcnow(),
            )
        )
        db.add(
            ClusterRow(
                cluster_id=cluster.cluster_id,
                run_id=run_id,
                site_id=cluster.site_id,
                theme=cluster.theme,
                week=week,
                volume=cluster.volume,
                neg=cluster.neg,
                pos=cluster.pos,
                net_sentiment=cluster.net_sentiment,
                confidence_band=cluster.confidence_band,
                item_ids=cluster.item_ids,
                source_type=cluster.source_type,
                payload=cluster.model_dump(mode="json"),
            )
        )
        db.add(
            DetectionRow(
                id="det1",
                run_id=run_id,
                cluster_id=cluster.cluster_id,
                spike=det.spike,
                compounding=det.compounding,
                cross_source=det.cross_source,
                priority=det.priority,
                payload={"cluster_id": cluster.cluster_id, "priority": det.priority},
            )
        )
        for item_id in cluster.item_ids:
            scored = scored_by_id.get(item_id)
            if scored:
                db.add(
                    FeedbackScored(
                        id=item_id,
                        run_id=run_id,
                        site_id=scored.site_id,
                        week=week,
                        primary_theme=scored.primary_theme,
                        themes=scored.themes,
                        sentiment=scored.sentiment,
                        urgency=scored.urgency,
                        relevant=scored.relevant,
                        score=scored.score,
                        rules_version=scored.rules_version,
                        channel=scored.channel,
                        source_type=scored.source_type,
                        text=scored.text,
                        payload=scored.model_dump(mode="json"),
                    )
                )
        db.commit()
        return cluster.cluster_id, week

    def test_enrich_detection_backfills_missing_root_cause_and_sla(self, db, rules):
        cluster_id, week = self._seed_run_with_detection(db, rules)
        row = db.query(DetectionRow).filter(DetectionRow.cluster_id == cluster_id).first()
        enriched = enrich_detection(db, row, week)
        assert enriched.root_cause is not None
        assert enriched.root_cause.get("summary")
        assert enriched.sla is not None
        assert enriched.sla.get("status") in ("on_track", "at_risk", "breached")

    def test_detections_for_week_returns_enriched(self, db, rules):
        cluster_id, week = self._seed_run_with_detection(db, rules)
        dets = detections_for_week(db, week)
        match = next(d for d in dets if d.cluster_id == cluster_id)
        assert match.root_cause is not None
        assert match.sla is not None

    def test_detection_for_cluster_detail(self, db, rules):
        cluster_id, week = self._seed_run_with_detection(db, rules)
        det = detection_for_cluster(db, cluster_id, week)
        assert det is not None
        assert det.priority == "P1"
        assert det.root_cause is not None
