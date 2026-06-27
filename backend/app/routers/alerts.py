from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas import SITE_BY_ID
from app.services import alerts_for_week, clusters_for_week, detections_for_week, get_week

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def alerts(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    rows = alerts_for_week(db, w)
    detections = detections_for_week(db, w)
    clusters = clusters_for_week(db, w)
    det_map = {d.cluster_id: d for d in detections}
    det_by_site_theme = {
        (c.site_id, c.theme): det_map[c.cluster_id]
        for c in clusters
        if c.cluster_id in det_map
    }
    settings = get_settings()
    webhook = bool(settings.teams_webhook_url)
    return {
        "week": w,
        "teams_webhook_configured": webhook,
        "delivery_mode": "teams_and_in_app" if webhook else "in_app_only",
        "description": (
            "Alerts are raised when the Detection Agent flags compounding, cross-source, or spike patterns. "
            "In production they post to a Microsoft Teams operations channel; this inbox shows the same messages."
        ),
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "site_id": a.site_id,
                "site_name": SITE_BY_ID.get(a.site_id, {}).get("name", a.site_id),
                "theme": a.theme,
                "theme_label": a.theme.replace("_", " ").title() if a.theme else None,
                "message": a.message,
                "priority": a.priority,
                "delivered_to_teams": a.payload.get("teams_delivered", False) if a.payload else False,
                "sla_status": _alert_field(a, det_by_site_theme, "sla", "status"),
                "sla_label": _alert_field(a, det_by_site_theme, "sla", "label"),
                "root_cause_summary": _alert_field(a, det_by_site_theme, "root_cause", "summary"),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ],
    }


def _alert_field(alert, det_by_site_theme: dict, section: str, key: str):
    det = det_by_site_theme.get((alert.site_id, alert.theme)) if alert.theme else None
    if det:
        block = getattr(det, section, None) or {}
        if isinstance(block, dict) and block.get(key):
            return block.get(key)
    payload = alert.payload or {}
    block = payload.get(section) or {}
    return block.get(key) if isinstance(block, dict) else None
