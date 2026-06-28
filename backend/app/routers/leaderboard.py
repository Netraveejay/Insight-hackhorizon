from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.leaderboard import build_leaderboard, prior_week
from app.services import clusters_for_week, detections_for_week, get_week, scored_for_week

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard")
def leaderboard(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    scored = scored_for_week(db, w)

    pw = prior_week(w)
    prior_clusters = clusters_for_week(db, pw) if pw else []

    return build_leaderboard(w, clusters, prior_clusters, detections, scored)
