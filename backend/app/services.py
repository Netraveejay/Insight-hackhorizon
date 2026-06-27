from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.root_cause import RootCauseAgent
from app.models import (
    AlertRow,
    AuditRecordRow,
    ClusterRow,
    DetectionRow,
    FeedbackRaw,
    FeedbackScored,
    InsightRow,
    LanguageStatsRow,
    RunRow,
    SourceCoverageRow,
)
from app.schemas import Cluster, Detection, Insight, ScoredItem
from app.rules import load_rules
from app.sla import compute_sla

_root_cause_agent = RootCauseAgent()


def latest_run(db: Session) -> RunRow | None:
    return db.query(RunRow).order_by(desc(RunRow.started_at)).first()


def get_week(db: Session, week: str | None) -> str:
    if week:
        return week
    run = latest_run(db)
    if run:
        return run.week
    from app.seed.generate import LATEST_WEEK

    return LATEST_WEEK


def clusters_for_week(db: Session, week: str, run_id: str | None = None) -> list[Cluster]:
    q = db.query(ClusterRow).filter(ClusterRow.week == week)
    if run_id:
        q = q.filter(ClusterRow.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(ClusterRow.run_id == run.id)
    return [Cluster.model_validate(c.payload) for c in q.all()]


def all_clusters(db: Session, run_id: str | None = None) -> list[Cluster]:
    q = db.query(ClusterRow)
    if run_id:
        q = q.filter(ClusterRow.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(ClusterRow.run_id == run.id)
    return [Cluster.model_validate(c.payload) for c in q.all()]


def _row_to_detection(row: DetectionRow) -> Detection:
    payload = row.payload or {}
    return Detection(
        cluster_id=row.cluster_id,
        spike=row.spike,
        compounding=row.compounding,
        cross_source=row.cross_source,
        priority=row.priority,
        root_cause=payload.get("root_cause"),
        sla=payload.get("sla"),
    )


def enrich_detection(
    db: Session,
    row: DetectionRow,
    week: str,
    triggered_at: datetime | None = None,
) -> Detection:
    """Backfill root cause + SLA for rows saved before enrichment was wired."""
    det = _row_to_detection(row)
    if not det.priority or (det.root_cause and det.sla):
        return det

    clusters = {c.cluster_id: c for c in clusters_for_week(db, week, row.run_id)}
    cluster = clusters.get(row.cluster_id)
    if not cluster:
        return det

    rules = load_rules()
    scored = scored_for_week(db, week, row.run_id)
    items = [s for s in scored if s.id in cluster.item_ids]

    if not det.root_cause:
        det = det.model_copy(update={"root_cause": _root_cause_agent.run(cluster, det, items, rules)})

    if not det.sla:
        run = db.query(RunRow).filter(RunRow.id == row.run_id).first()
        at = triggered_at or (run.started_at if run else None) or datetime.utcnow()
        det = det.model_copy(update={"sla": compute_sla(det.priority, at, rules.sla)})

    return det


def detections_for_week(db: Session, week: str, run_id: str | None = None) -> list[Detection]:
    cluster_ids = [c.cluster_id for c in clusters_for_week(db, week, run_id)]
    q = db.query(DetectionRow).filter(DetectionRow.cluster_id.in_(cluster_ids))
    if run_id:
        q = q.filter(DetectionRow.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(DetectionRow.run_id == run.id)
    return [enrich_detection(db, d, week) for d in q.all()]


def detection_for_cluster(db: Session, cluster_id: str, week: str) -> Detection | None:
    run = latest_run(db)
    q = db.query(DetectionRow).filter(DetectionRow.cluster_id == cluster_id)
    if run:
        q = q.filter(DetectionRow.run_id == run.id)
    row = q.first()
    if not row:
        return None
    return enrich_detection(db, row, week)


def insights_for_week(db: Session, week: str, run_id: str | None = None) -> list[Insight]:
    cluster_ids = [c.cluster_id for c in clusters_for_week(db, week, run_id)]
    q = db.query(InsightRow).filter(InsightRow.cluster_id.in_(cluster_ids))
    if run_id:
        q = q.filter(InsightRow.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(InsightRow.run_id == run.id)
    return [
        Insight(
            cluster_id=i.cluster_id,
            insight=i.insight,
            evidence_sample=i.evidence_sample,
            owner_suggested=i.owner_suggested,
            rules_version=i.rules_version,
            status=i.status,
            draft_source=i.draft_source,
        )
        for i in q.all()
    ]


def scored_for_week(db: Session, week: str, run_id: str | None = None) -> list[ScoredItem]:
    q = db.query(FeedbackScored).filter(FeedbackScored.week == week)
    if run_id:
        q = q.filter(FeedbackScored.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(FeedbackScored.run_id == run.id)
    return [ScoredItem.model_validate(s.payload) for s in q.all()]


def all_scored(db: Session, run_id: str | None = None) -> list[ScoredItem]:
    q = db.query(FeedbackScored)
    if run_id:
        q = q.filter(FeedbackScored.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(FeedbackScored.run_id == run.id)
    return [ScoredItem.model_validate(s.payload) for s in q.all()]


def raw_for_week(db: Session, week: str, run_id: str | None = None) -> list[dict]:
    q = db.query(FeedbackRaw).filter(FeedbackRaw.week == week)
    if run_id:
        q = q.filter(FeedbackRaw.run_id == run_id)
    else:
        run = latest_run(db)
        if run:
            q = q.filter(FeedbackRaw.run_id == run.id)
    return [r.payload for r in q.all()]


def coverage_for_run(db: Session, run_id: str | None = None):
    from app.schemas import SourceCoverageEntry, SourceCoverageReport
    from datetime import datetime

    run = db.query(RunRow).filter(RunRow.id == run_id).first() if run_id else latest_run(db)
    if not run:
        return SourceCoverageReport(run_id="none", entries=[])
    rows = db.query(SourceCoverageRow).filter(SourceCoverageRow.run_id == run.id).all()
    return SourceCoverageReport(
        run_id=run.id,
        entries=[
            SourceCoverageEntry(
                connector=r.connector,
                status=r.status,
                item_count=r.item_count,
                message=r.message,
            )
            for r in rows
        ],
        timestamp=run.started_at or datetime.utcnow(),
    )


def alerts_for_week(db: Session, week: str) -> list[AlertRow]:
    run = latest_run(db)
    q = db.query(AlertRow).filter(AlertRow.week == week)
    if run:
        q = q.filter(AlertRow.run_id == run.id)
    return q.order_by(desc(AlertRow.created_at)).all()


def audit_for_item(db: Session, item_id: str) -> list[dict]:
    rows = db.query(AuditRecordRow).filter(AuditRecordRow.item_id == item_id).all()
    return [
        {
            "item_id": r.item_id,
            "snapshot_at_ingest": r.snapshot_at_ingest,
            "original_text": r.original_text,
            "original_language": r.original_language,
            "translated_text": r.translated_text,
            "translation_provider": r.translation_provider,
            "classification": r.classification,
            "score": r.score,
            "rules_version": r.rules_version,
            "confidence_band": r.confidence_band,
        }
        for r in rows
    ]


def language_stats_for_week(db: Session, week: str):
    from app.schemas import LanguageStat, LanguageStatsReport

    run = latest_run(db)
    if not run:
        return None
    rows = db.query(LanguageStatsRow).filter(
        LanguageStatsRow.run_id == run.id, LanguageStatsRow.week == week
    ).all()
    if not rows:
        return None
    return LanguageStatsReport(
        run_id=run.id,
        week=week,
        languages=[
            LanguageStat(language=r.language, count=r.count, translated_count=r.translated_count)
            for r in rows
        ],
        total_items=sum(r.count for r in rows),
    )
