from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.output import OutputAgent
from app.db import get_db
from app.services import (
    clusters_for_week,
    coverage_for_run,
    detections_for_week,
    get_week,
    insights_for_week,
    language_stats_for_week,
    scored_for_week,
)
from app.schemas import SITE_BY_ID

router = APIRouter(tags=["overview"])


@router.get("/overview")
def overview(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    scored = scored_for_week(db, w)
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    insights = insights_for_week(db, w)
    stats = language_stats_for_week(db, w)
    return OutputAgent().render_overview(scored, clusters, detections, insights, w, stats)
