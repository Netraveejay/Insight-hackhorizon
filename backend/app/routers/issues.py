from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ClusterRow, DetectionRow, InsightRow
from app.schemas import SITE_BY_ID
from app.services import audit_for_item, clusters_for_week, detection_for_cluster, detections_for_week, get_week, insights_for_week, scored_for_week
from app.issue_detail import audit_timeline, channel_label, detection_summary

router = APIRouter(tags=["issues"])


@router.get("/issues")
def issues(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    insights = insights_for_week(db, w)
    det_map = {d.cluster_id: d for d in detections}
    ins_map = {i.cluster_id: i for i in insights}

    result = []
    for c in clusters:
        d = det_map.get(c.cluster_id)
        if not d or not d.priority:
            continue
        ins = ins_map.get(c.cluster_id)
        result.append(
            {
                "cluster_id": c.cluster_id,
                "site_id": c.site_id,
                "site_name": SITE_BY_ID.get(c.site_id, {}).get("name", c.site_id),
                "theme": c.theme,
                "week": c.week,
                "volume": c.volume,
                "neg": c.neg,
                "pos": c.pos,
                "confidence_band": c.confidence_band,
                "priority": d.priority,
                "flags": {
                    "cross_source": bool(d.cross_source),
                    "compounding": bool(d.compounding),
                    "spike": bool(d.spike),
                },
                "insight_preview": ins.insight[:120] if ins else None,
                "root_cause_summary": (d.root_cause or {}).get("summary"),
                "sla_status": (d.sla or {}).get("status"),
            }
        )
    priority_order = {"P1": 0, "P2": 1, "P3": 2}
    result.sort(key=lambda x: (priority_order.get(x["priority"], 9), -x["neg"]))
    return {"week": w, "issues": result}


@router.get("/issues/{cluster_id}")
def issue_detail(cluster_id: str, db: Session = Depends(get_db)):
    cluster_row = db.query(ClusterRow).filter(ClusterRow.cluster_id == cluster_id).first()
    if not cluster_row:
        raise HTTPException(404, "Cluster not found")

    det_row = db.query(DetectionRow).filter(DetectionRow.cluster_id == cluster_id).first()
    ins_row = db.query(InsightRow).filter(InsightRow.cluster_id == cluster_id).first()
    det = detection_for_cluster(db, cluster_id, cluster_row.week)
    root_cause = det.root_cause if det else None
    sla = det.sla if det else None
    scored = scored_for_week(db, cluster_row.week)

    cluster_items = [s for s in scored if s.id in (cluster_row.item_ids or [])]
    negatives = [s for s in cluster_items if s.sentiment.get(s.primary_theme) == "negative"]
    others = [s for s in cluster_items if s not in negatives]
    ordered_items = negatives + others

    evidence = []
    for item in ordered_items:
        audit_rows = audit_for_item(db, item.id)
        evidence.append(
            {
                "id": item.id,
                "text": item.text,
                "original_text": item.original_text,
                "original_language": item.original_language,
                "translated": item.translated,
                "channel": item.channel,
                "channel_label": channel_label(item.channel),
                "source_type": item.source_type,
                "rating": item.rating,
                "sentiment": item.sentiment.get(item.primary_theme, "neutral"),
                "urgency": item.urgency,
                "ts": item.ts.isoformat(),
                "timeline": audit_timeline(audit_rows),
            }
        )

    site_name = SITE_BY_ID.get(cluster_row.site_id, {}).get("name", cluster_row.site_id)
    theme_label = cluster_row.theme.replace("_", " ").title()

    return {
        "cluster_id": cluster_id,
        "site_id": cluster_row.site_id,
        "site_name": site_name,
        "theme": cluster_row.theme,
        "theme_label": theme_label,
        "week": cluster_row.week,
        "volume": cluster_row.volume,
        "neg": cluster_row.neg,
        "pos": cluster_row.pos,
        "confidence_band": cluster_row.confidence_band,
        "source_type": cluster_row.source_type,
        "priority": det_row.priority if det_row else None,
        "signals": detection_summary(det_row),
        "root_cause": root_cause,
        "sla": sla,
        "recommendation": {
            "text": ins_row.insight if ins_row else None,
            "owner": ins_row.owner_suggested if ins_row else None,
            "status": ins_row.status if ins_row else None,
            "draft_source": ins_row.draft_source if ins_row else None,
        },
        "evidence": evidence,
        "evidence_count": len(cluster_items),
    }
