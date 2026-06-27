from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.output import OutputAgent
from app.db import get_db
from app.services import get_week, language_stats_for_week

router = APIRouter(tags=["languages"])


@router.get("/languages")
def languages(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    stats = language_stats_for_week(db, w)
    if not stats:
        return {"week": w, "total_items": 0, "languages": []}
    return OutputAgent().render_language_summary(stats)
