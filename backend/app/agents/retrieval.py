"""Read-only retrieval tools for the Assistant — every answer must trace here."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.output import OutputAgent
from app.models import ClusterRow, FeedbackScored, RunRow
from app.schemas import SITE_BY_ID
from app.services import (
    all_clusters,
    clusters_for_week,
    detections_for_week,
    detection_for_cluster,
    get_week,
    insights_for_week,
    language_stats_for_week,
    scored_for_week,
)
from app.sla import compute_sla
from app.rules import load_rules


def get_top_issues(db: Session, week: str | None = None) -> dict:
    w = get_week(db, week)
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    insights = insights_for_week(db, w)
    scored = scored_for_week(db, w)
    overview = OutputAgent().render_overview(scored, clusters, detections, insights, w)
    return {"week": w, "overview": overview}


def get_site(db: Session, site_id: str, week: str | None = None) -> dict:
    w = get_week(db, week)
    site = SITE_BY_ID.get(site_id)
    clusters = [c for c in clusters_for_week(db, w) if c.site_id == site_id]
    clusters.sort(key=lambda c: -c.neg)
    detections = {d.cluster_id: d for d in detections_for_week(db, w)}
    return {
        "week": w,
        "site_id": site_id,
        "site_name": site["name"] if site else site_id,
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "theme": c.theme,
                "neg": c.neg,
                "volume": c.volume,
                "priority": detections.get(c.cluster_id).priority if detections.get(c.cluster_id) else None,
            }
            for c in clusters[:10]
        ],
    }


def get_cluster(db: Session, cluster_id: str, week: str | None = None) -> dict:
    w = get_week(db, week)
    clusters = clusters_for_week(db, w)
    cluster = next((c for c in clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return {"week": w, "cluster_id": cluster_id, "found": False}
    det = detection_for_cluster(db, cluster_id, w)
    ins = next((i for i in insights_for_week(db, w) if i.cluster_id == cluster_id), None)
    return {
        "week": w,
        "found": True,
        "cluster": cluster.model_dump(mode="json"),
        "detection": det.model_dump(mode="json") if det else None,
        "insight": ins.model_dump(mode="json") if ins else None,
    }


def get_theme_trend(db: Session, theme: str) -> dict:
    run = db.query(RunRow).order_by(desc(RunRow.started_at)).first()
    if not run:
        return {"theme": theme, "weeks": []}
    rows = (
        db.query(ClusterRow)
        .filter(ClusterRow.run_id == run.id, ClusterRow.theme.contains(theme))
        .all()
    )
    by_week: dict[str, dict] = {}
    for row in rows:
        wk = row.week
        if wk not in by_week:
            by_week[wk] = {"week": wk, "neg": 0, "volume": 0, "sites": set()}
        by_week[wk]["neg"] += row.neg
        by_week[wk]["volume"] += row.volume
        by_week[wk]["sites"].add(row.site_id)
    weeks = []
    for wk, data in sorted(by_week.items()):
        weeks.append({
            "week": wk,
            "neg": data["neg"],
            "volume": data["volume"],
            "site_count": len(data["sites"]),
        })
    return {"theme": theme, "weeks": weeks}


def get_root_cause(db: Session, cluster_id: str, week: str | None = None) -> dict:
    w = get_week(db, week)
    det = detection_for_cluster(db, cluster_id, w)
    if not det or not det.root_cause:
        return {"week": w, "cluster_id": cluster_id, "found": False}
    return {
        "week": w,
        "cluster_id": cluster_id,
        "found": True,
        "priority": det.priority,
        "root_cause": det.root_cause,
    }


def get_detections(db: Session, week: str | None = None, kind: str | None = None) -> dict:
    w = get_week(db, week)
    detections = detections_for_week(db, w)
    if kind == "cross_source":
        detections = [d for d in detections if d.cross_source]
    elif kind == "compounding":
        detections = [d for d in detections if d.compounding]
    elif kind == "spike":
        detections = [d for d in detections if d.spike]
    clusters = {c.cluster_id: c for c in clusters_for_week(db, w)}
    items = []
    for d in detections:
        c = clusters.get(d.cluster_id)
        if not c:
            continue
        items.append({
            "cluster_id": d.cluster_id,
            "site_id": c.site_id,
            "site_name": SITE_BY_ID.get(c.site_id, {}).get("name", c.site_id),
            "theme": c.theme,
            "week": c.week,
            "priority": d.priority,
            "neg": c.neg,
        })
    return {"week": w, "kind": kind, "count": len(items), "detections": items}


def get_sla_status(db: Session, week: str | None = None) -> dict:
    w = get_week(db, week)
    detections = detections_for_week(db, w)
    summary = {"on_track": 0, "at_risk": 0, "breached": 0}
    items = []
    for d in detections:
        if not d.priority or not d.sla:
            continue
        st = d.sla.get("status", "on_track")
        summary[st] = summary.get(st, 0) + 1
        c = next((x for x in clusters_for_week(db, w) if x.cluster_id == d.cluster_id), None)
        items.append({
            "cluster_id": d.cluster_id,
            "site_id": c.site_id if c else None,
            "theme": c.theme if c else None,
            "priority": d.priority,
            "sla_status": st,
            "sla_label": d.sla.get("label"),
        })
    return {"week": w, "summary": summary, "items": items}


def get_language_mix(db: Session, week: str | None = None) -> dict:
    w = get_week(db, week)
    stats = language_stats_for_week(db, w)
    if not stats:
        return {"week": w, "languages": []}
    return {
        "week": w,
        "languages": [
            {"language": ls.language, "count": ls.count, "translated": ls.translated_count}
            for ls in stats.languages
        ],
    }


def get_positive_themes(db: Session, week: str | None = None) -> dict:
    w = get_week(db, week)
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    insights = insights_for_week(db, w)
    scored = scored_for_week(db, w)
    overview = OutputAgent().render_overview(scored, clusters, detections, insights, w)
    return {"week": w, "positive_themes": overview.get("positive_themes", [])}


def get_negative_feedback(
    db: Session,
    week: str | None = None,
    limit: int = 10,
    site_id: str | None = None,
    theme: str | None = None,
) -> dict:
    """Ranked negative guest comments — sorted by score (most negative first)."""
    w = get_week(db, week)
    run = db.query(RunRow).order_by(desc(RunRow.started_at)).first()
    query = db.query(FeedbackScored).filter(FeedbackScored.week == w)
    if run:
        query = query.filter(FeedbackScored.run_id == run.id)
    items: list[dict] = []
    for row in query.all():
        theme_key = row.primary_theme
        if row.sentiment.get(theme_key) != "negative":
            continue
        if site_id and row.site_id != site_id:
            continue
        if theme and row.primary_theme != theme and theme not in (row.themes or []):
            continue
        site = SITE_BY_ID.get(row.site_id, {})
        items.append({
            "id": row.id,
            "site_id": row.site_id,
            "site_name": site.get("name", row.site_id),
            "channel": row.channel,
            "theme": row.primary_theme,
            "text": (row.text or "")[:220],
            "score": row.score,
            "urgency": row.urgency,
        })
    items.sort(key=lambda x: x["score"])
    items = items[:limit]
    return {"week": w, "limit": limit, "count": len(items), "items": items}


def search_feedback(db: Session, text: str, week: str | None = None, limit: int = 10) -> dict:
    w = get_week(db, week)
    q = text.lower()
    run = db.query(RunRow).order_by(desc(RunRow.started_at)).first()
    query = db.query(FeedbackScored).filter(FeedbackScored.week == w)
    if run:
        query = query.filter(FeedbackScored.run_id == run.id)
    matches = []
    for row in query.all():
        body = (row.text or "").lower()
        if q in body:
            payload = row.payload or {}
            matches.append({
                "id": row.id,
                "site_id": row.site_id,
                "channel": row.channel,
                "text": row.text[:160],
                "original_language": payload.get("original_language", "en"),
                "translated": payload.get("translated", False),
            })
        if len(matches) >= limit:
            break
    return {"week": w, "query": text, "count": len(matches), "matches": matches}


RETRIEVAL_TOOLS = {
    "get_top_issues": get_top_issues,
    "get_site": get_site,
    "get_cluster": get_cluster,
    "get_theme_trend": get_theme_trend,
    "get_root_cause": get_root_cause,
    "get_detections": get_detections,
    "get_sla_status": get_sla_status,
    "get_language_mix": get_language_mix,
    "get_positive_themes": get_positive_themes,
    "get_negative_feedback": get_negative_feedback,
    "search_feedback": search_feedback,
}
