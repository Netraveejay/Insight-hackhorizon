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
    scored_for_week,
)

router = APIRouter(tags=["digest"])


@router.get("/digest")
def digest(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    return OutputAgent().render_digest(
        clusters_for_week(db, w),
        detections_for_week(db, w),
        insights_for_week(db, w),
        scored_for_week(db, w),
        coverage_for_run(db),
        w,
    )


@router.get("/summary")
def summary(month: str = "2026-06", db: Session = Depends(get_db)):
    from app.services import all_clusters, detections_for_week, get_week

    w = get_week(db, None)
    return OutputAgent().render_summary(all_clusters(db), detections_for_week(db, w), month)
