from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import RunRow
from app.orchestrator import Orchestrator

router = APIRouter(tags=["pipeline"])


@router.get("/pipeline/runs")
def list_runs(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(RunRow).order_by(desc(RunRow.started_at)).limit(limit).all()
    return {
        "runs": [
            {
                "id": r.id,
                "cadence": r.cadence,
                "week": r.week,
                "rules_version": r.rules_version,
                "status": r.status,
                "stats": r.stats,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ]
    }


@router.get("/pipeline/explain")
def explain_pipeline(week: str | None = None, db: Session = Depends(get_db)):
    """Return plain-language explanation from the most recent pipeline run."""
    q = db.query(RunRow).filter(RunRow.status == "completed")
    if week:
        q = q.filter(RunRow.week == week)
    row = q.order_by(desc(RunRow.completed_at)).first()
    if not row or not row.stats.get("explanation"):
        raise HTTPException(
            status_code=404,
            detail="No pipeline explanation yet — run POST /pipeline/run first",
        )
    return {
        "run_id": row.id,
        "week": row.week,
        "explanation": row.stats["explanation"],
    }


@router.post("/pipeline/run")
def run_pipeline(week: str | None = None):
    """Trigger the full agent pipeline — demo entry point."""
    db = SessionLocal()
    try:
        result = Orchestrator(db).run_pipeline(week=week, cadence="manual")
        return result.model_dump()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()
