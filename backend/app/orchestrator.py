from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.clustering import ClusteringAgent
from app.agents.detection import DetectionAgent
from app.agents.explainability import ExplainabilityAgent
from app.agents.ingestion import IngestionAgent
from app.agents.insight import InsightAgent
from app.agents.output import OutputAgent
from app.agents.scoring import ScoringAgent
from app.agents.root_cause import RootCauseAgent
from app.agents.translation import TranslationAgent
from app.audit import write_ingest_audit, write_lineage, write_score_audit, write_translation_audit
from app.connectors.registry import load_connectors
from app.models import (
    AlertRow,
    AuditRecordRow,
    ClusterRow,
    DetectionRow,
    DistributionLogRow,
    FeedbackRaw,
    FeedbackScored,
    FeedbackTranslated,
    GeneratedReportRow,
    InsightRow,
    LanguageStatsRow,
    RunRow,
    SourceCoverageRow,
)
from app.reports.generator import ReportGenerator
from app.rules import load_rules
from app.sla import compute_sla
from app.schemas import Cluster, Detection, PipelineRunResult, ScoredItem, TranslatedItem

logger = logging.getLogger(__name__)


class Orchestrator:
    """Thin sequencer: ingest → translate → score → cluster → detect → insight → output."""

    def __init__(self, db: Session):
        self.db = db
        self.ingestion = IngestionAgent()
        self.translation = TranslationAgent()
        self.scoring = ScoringAgent()
        self.clustering = ClusteringAgent()
        self.detection = DetectionAgent()
        self.insight = InsightAgent()
        self.output = OutputAgent()
        self.explainability = ExplainabilityAgent()
        self.root_cause = RootCauseAgent()

    def run_pipeline(self, week: str | None = None, cadence: str = "manual") -> PipelineRunResult:
        rules = load_rules()
        run_id = str(uuid.uuid4())[:12]
        if not week:
            week = self._latest_week()

        self._clear_pipeline_artifacts(self.db)

        run = RunRow(id=run_id, cadence=cadence, week=week, rules_version=rules.version, status="running")
        self.db.add(run)
        self.db.flush()

        steps: list[dict] = []

        connectors = load_connectors()
        raw_items: list = []
        coverage_entries = []
        for connector in connectors:
            items, cov = connector.fetch(week=None)
            raw_items.extend(items)
            coverage_entries.append(cov)
        ingested, coverage_report = self.ingestion.run(raw_items, coverage_entries, rules, run_id)
        steps.append({
            "id": "ingest",
            "label": "Ingestion",
            "detail": f"{len(ingested)} items normalised · dedupe · spam · PII",
            "count": len(ingested),
            "status": "completed",
        })

        for entry in coverage_report.entries:
            self.db.add(
                SourceCoverageRow(
                    id=str(uuid.uuid4())[:16],
                    run_id=run_id,
                    connector=entry.connector,
                    status=entry.status,
                    item_count=entry.item_count,
                    message=entry.message,
                )
            )

        translated, lang_stats = self.translation.run_batch(ingested, rules, run_id, week)
        translated_count = sum(1 for t in translated if t.translated)
        steps.append({
            "id": "translate",
            "label": "Translation",
            "detail": f"{translated_count} non-English → English · originals retained",
            "count": translated_count,
            "status": "completed",
        })
        for ls in lang_stats.languages:
            self.db.add(
                LanguageStatsRow(
                    id=str(uuid.uuid4())[:16],
                    run_id=run_id,
                    week=week,
                    language=ls.language,
                    count=ls.count,
                    translated_count=ls.translated_count,
                )
            )

        scored: list[ScoredItem] = []
        for item in translated:
            write_ingest_audit(self.db, run_id, item)
            write_translation_audit(self.db, run_id, item)
            result = self.scoring.run(item, rules)
            if result:
                scored.append(result)
                self.db.merge(self._scored_row(result, run_id))
                self.db.merge(self._translated_row(item, run_id))
                write_score_audit(self.db, run_id, result)
        steps.append({
            "id": "score",
            "label": "Scoring",
            "detail": f"Deterministic themes · sentiment · rules v{rules.version}",
            "count": len(scored),
            "status": "completed",
        })

        all_clusters = self.clustering.run(scored, rules)
        current_clusters = [c for c in all_clusters if c.week == week]
        staff_clusters = [c for c in all_clusters if c.source_type in ("staff", "mixed")]

        for c in current_clusters:
            self.db.merge(self._cluster_row(c, run_id))
            write_lineage(self.db, run_id, "clustering", c.cluster_id, c.model_dump(mode="json"))
        steps.append({
            "id": "cluster",
            "label": "Clustering",
            "detail": f"{len(current_clusters)} site×theme×week clusters for {week}",
            "count": len(current_clusters),
            "status": "completed",
        })

        detections = self.detection.run(current_clusters, all_clusters, staff_clusters, rules)
        triggered_at = datetime.utcnow()
        cluster_map = {c.cluster_id: c for c in current_clusters}
        enriched_detections: list[Detection] = []
        for d in detections:
            if d.priority:
                c = cluster_map.get(d.cluster_id)
                if c:
                    items = [s for s in scored if s.id in c.item_ids]
                    rc = self.root_cause.run(c, d, items, rules)
                    sla = compute_sla(d.priority, triggered_at, rules.sla)
                    d = d.model_copy(update={"root_cause": rc, "sla": sla})
            enriched_detections.append(d)
        detections = enriched_detections

        for d in detections:
            self.db.add(self._detection_row(d, run_id))
            write_lineage(self.db, run_id, "detection", d.cluster_id, d.model_dump(mode="json"))
        p1 = [d for d in detections if d.priority == "P1"]
        steps.append({
            "id": "detect",
            "label": "Detection",
            "detail": f"{len(detections)} flags · {len(p1)} P1 cross-source/compounding",
            "count": len(detections),
            "status": "completed",
        })

        det_map = {d.cluster_id: d for d in detections}
        insights = []
        for c in current_clusters:
            d = det_map.get(c.cluster_id)
            if d and d.priority in ("P1", "P2", "P3"):
                ins = self.insight.run(c, d, scored, rules.version)
                insights.append(ins)
                self.db.add(self._insight_row(ins, run_id))
        steps.append({
            "id": "insight",
            "label": "Insight Agent",
            "detail": f"{len(insights)} draft recommendations (internal only)",
            "count": len(insights),
            "status": "completed",
        })

        for s in scored:
            if s.channel == "disruption_notification" and s.week == week:
                self.output.create_disruption_alert(self.db, run_id, week, s.site_id, s.text)

        alerts = self.output.distribute(
            self.db, run_id, week, current_clusters, detections, insights, coverage_report, lang_stats
        )

        reports = ReportGenerator().generate_all(
            self.db, run_id, week, current_clusters, detections, insights, scored, coverage_report
        )
        # Link distribution log entries to generated files
        for log in self.db.query(DistributionLogRow).filter(DistributionLogRow.run_id == run_id).all():
            if log.target_type == "digest":
                digest = next((r for r in reports if r.report_type == "digest"), None)
                if digest:
                    log.payload_summary = f"{log.payload_summary} · file: {digest.file_name}"
            elif log.target_type == "email":
                site_id = log.target.split("@")[0]
                site_report = next((r for r in reports if r.site_id == site_id), None)
                if site_report:
                    log.payload_summary = f"{log.payload_summary} · file: {site_report.file_name}"

        steps.append({
            "id": "output",
            "label": "Output & Distribution",
            "detail": f"{len(alerts)} Teams alerts · digest · 21 site reports queued",
            "count": len(alerts),
            "status": "completed",
        })

        explanation = self.explainability.run(
            week=week,
            run_id=run_id,
            rules_version=rules.version,
            cadence=cadence,
            ingested=ingested,
            translated=translated,
            scored=scored,
            current_clusters=current_clusters,
            detections=detections,
            insights=insights,
            alerts_count=len(alerts),
            hero_cluster_id=p1[0].cluster_id if p1 else None,
        )
        steps.append({
            "id": "explain",
            "label": "Explainability Agent",
            "detail": "Plain-language narrative for operators",
            "count": len(explanation.steps),
            "status": "completed",
        })

        for item in translated:
            if item.week == week:
                self.db.merge(
                    FeedbackRaw(
                        id=item.id,
                        run_id=run_id,
                        source_type=item.source_type,
                        channel=item.channel,
                        site_id=item.site_id,
                        ts=item.ts,
                        week=item.week,
                        rating=item.rating,
                        text=item.original_text,
                        payload=item.model_dump(mode="json"),
                    )
                )

        hero_cluster_id = p1[0].cluster_id if p1 else None
        outputs = [
            {"type": "issues", "label": "Prioritised issues", "count": len([d for d in detections if d.priority])},
            {"type": "alerts", "label": "Teams alerts", "count": len(alerts)},
            {"type": "insights", "label": "Draft recommendations", "count": len(insights)},
            {"type": "digest", "label": "Executive digest", "count": 1},
            {"type": "sites", "label": "Per-site reports", "count": len(reports) - 1},
            {"type": "reports", "label": "Downloadable HTML reports", "count": len(reports)},
        ]

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.stats = {
            "items_ingested": len(ingested),
            "items_translated": translated_count,
            "items_scored": len(scored),
            "clusters": len(current_clusters),
            "detections": len(detections),
            "insights": len(insights),
            "hero_cluster_id": hero_cluster_id,
            "explanation": explanation.model_dump(mode="json"),
        }
        self.db.commit()

        return PipelineRunResult(
            run_id=run_id,
            week=week,
            items_ingested=len(ingested),
            items_translated=translated_count,
            items_scored=len(scored),
            clusters=len(current_clusters),
            detections=len(detections),
            insights=len(insights),
            rules_version=rules.version,
            steps=steps,
            hero_cluster_id=hero_cluster_id,
            outputs=outputs,
            explanation=explanation.model_dump(mode="json"),
        )

    def _clear_pipeline_artifacts(self, db: Session) -> None:
        """Allow idempotent re-runs — clear computed artifacts, keep run history."""
        from app.config import get_settings

        settings = get_settings()
        reports_path = settings.resolved_reports_path
        if reports_path.exists():
            import shutil

            shutil.rmtree(reports_path, ignore_errors=True)

        for model in (
            AlertRow,
            AuditRecordRow,
            ClusterRow,
            DetectionRow,
            DistributionLogRow,
            FeedbackRaw,
            FeedbackScored,
            FeedbackTranslated,
            GeneratedReportRow,
            InsightRow,
            LanguageStatsRow,
            SourceCoverageRow,
        ):
            db.query(model).delete()
        db.flush()

    def _latest_week(self) -> str:
        from app.seed.generate import RECENT_WEEKS

        return RECENT_WEEKS[-1]

    def _translated_row(self, item: TranslatedItem, run_id: str) -> FeedbackTranslated:
        return FeedbackTranslated(
            id=item.id,
            run_id=run_id,
            site_id=item.site_id,
            week=item.week,
            original_text=item.original_text,
            original_language=item.original_language,
            text=item.text,
            translated=item.translated,
            translation_provider=item.translation_provider,
            translation_confidence=item.translation_confidence,
            payload=item.model_dump(mode="json"),
        )

    def _scored_row(self, item: ScoredItem, run_id: str) -> FeedbackScored:
        return FeedbackScored(
            id=item.id,
            run_id=run_id,
            site_id=item.site_id,
            week=item.week,
            primary_theme=item.primary_theme,
            themes=item.themes,
            sentiment=item.sentiment,
            urgency=item.urgency,
            relevant=item.relevant,
            score=item.score,
            rules_version=item.rules_version,
            channel=item.channel,
            source_type=item.source_type,
            text=item.text,
            payload=item.model_dump(mode="json"),
        )

    def _cluster_row(self, c: Cluster, run_id: str) -> ClusterRow:
        return ClusterRow(
            cluster_id=c.cluster_id,
            run_id=run_id,
            site_id=c.site_id,
            theme=c.theme,
            week=c.week,
            volume=c.volume,
            neg=c.neg,
            pos=c.pos,
            net_sentiment=c.net_sentiment,
            confidence_band=c.confidence_band,
            item_ids=c.item_ids,
            source_type=c.source_type,
            payload=c.model_dump(mode="json"),
        )

    def _detection_row(self, d: Detection, run_id: str) -> DetectionRow:
        return DetectionRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            cluster_id=d.cluster_id,
            spike=d.spike,
            compounding=d.compounding,
            cross_source=d.cross_source,
            priority=d.priority,
            payload=d.model_dump(mode="json"),
        )

    def _insight_row(self, ins, run_id: str) -> InsightRow:
        return InsightRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            cluster_id=ins.cluster_id,
            insight=ins.insight,
            evidence_sample=ins.evidence_sample,
            owner_suggested=ins.owner_suggested,
            rules_version=ins.rules_version,
            status=ins.status,
            draft_source=ins.draft_source,
            payload=ins.model_dump(mode="json"),
        )
