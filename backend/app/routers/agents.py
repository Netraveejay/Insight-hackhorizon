from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.metrics.accuracy import compute_accuracy_report
from app.models import FeedbackRaw

router = APIRouter(tags=["agents"])


@router.get("/agents/accuracy")
def agents_accuracy(db: Session = Depends(get_db)):
    """Report measured accuracy of deterministic agents on seed-labelled data."""
    rows = db.query(FeedbackRaw).all()
    payloads = [r.payload for r in rows]
    if not payloads:
        return {
            "message": "No data yet — run make seed first",
            "report": compute_accuracy_report([]),
        }
    return {"report": compute_accuracy_report(payloads)}
