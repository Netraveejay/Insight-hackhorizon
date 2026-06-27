from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import all_clusters, detections_for_week, get_week, scored_for_week
from app.seed.generate import RECENT_WEEKS

router = APIRouter(tags=["trends"])


@router.get("/trends")
def trends(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    clusters = all_clusters(db)
    detections = detections_for_week(db, w)

    # Compounding series: guest vs staff negatives by week for hero themes
    compounding_series = []
    for theme in ["projection_quality", "ticketing_queue", "f_and_b"]:
        for week_str in RECENT_WEEKS:
            guest_neg = sum(
                c.neg for c in clusters if c.theme == theme and c.week == week_str and c.source_type in ("guest", "mixed")
            )
            staff_neg = sum(
                c.neg for c in clusters if c.theme == theme and c.week == week_str and c.source_type in ("staff", "mixed")
            )
            compounding_series.append(
                {"week": week_str, "theme": theme, "guest_neg": guest_neg, "staff_neg": staff_neg}
            )

    # National theme trajectories
    theme_weeks: dict[str, list] = {}
    for c in clusters:
        theme_weeks.setdefault(c.theme, []).append({"week": c.week, "neg": c.neg, "pos": c.pos, "volume": c.volume})

    trajectories = []
    for theme, series in theme_weeks.items():
        by_week = {}
        for s in series:
            if s["week"] not in by_week:
                by_week[s["week"]] = {"neg": 0, "pos": 0, "volume": 0}
            by_week[s["week"]]["neg"] += s["neg"]
            by_week[s["week"]]["pos"] += s["pos"]
            by_week[s["week"]]["volume"] += s["volume"]
        weeks_sorted = sorted(by_week.keys())
        negs = [by_week[w]["neg"] for w in weeks_sorted]
        direction = "stable"
        if len(negs) >= 2:
            if negs[-1] > negs[0]:
                direction = "rising"
            elif negs[-1] < negs[0]:
                direction = "falling"
        trajectories.append(
            {
                "theme": theme,
                "direction": direction,
                "series": [{"week": w, **by_week[w]} for w in weeks_sorted],
            }
        )
    trajectories.sort(key=lambda x: -sum(p["neg"] for p in x["series"]))

    compounding_detections = [
        {
            "cluster_id": d.cluster_id,
            "compounding": d.compounding,
            "cross_source": d.cross_source,
            "priority": d.priority,
        }
        for d in detections
        if d.compounding
    ]

    return {
        "week": w,
        "compounding_series": compounding_series,
        "compounding_detections": compounding_detections,
        "theme_trajectories": trajectories[:10],
    }
