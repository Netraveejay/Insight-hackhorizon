from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.output import OutputAgent
from app.db import get_db
from app.schemas import SITES
from app.services import (
    clusters_for_week,
    detections_for_week,
    get_week,
    insights_for_week,
    scored_for_week,
)

router = APIRouter(tags=["sites"])


@router.get("/sites")
def list_sites():
    return {"sites": SITES}


@router.get("/sites/{site_id}")
def site_report(site_id: str, week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    return OutputAgent().render_site_report(
        site_id,
        clusters_for_week(db, w),
        detections_for_week(db, w),
        insights_for_week(db, w),
        scored_for_week(db, w),
        w,
    )
