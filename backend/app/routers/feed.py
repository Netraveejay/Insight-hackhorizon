from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.issue_detail import channel_label
from app.schemas import SITE_BY_ID
from app.services import coverage_for_run, get_week, raw_for_week, scored_for_week

router = APIRouter(tags=["feed"])


def _item_card(item: dict, *, status: str = "active") -> dict:
    site_id = item.get("site_id", "")
    return {
        "id": item.get("id"),
        "source_type": item.get("source_type"),
        "channel": item.get("channel"),
        "channel_label": channel_label(item.get("channel", "")),
        "site_id": site_id,
        "site_name": SITE_BY_ID.get(site_id, {}).get("name", site_id),
        "text": item.get("text"),
        "original_text": item.get("original_text"),
        "original_language": item.get("original_language"),
        "translated": item.get("translated", False),
        "rating": item.get("rating"),
        "ts": item.get("ts"),
        "is_spam": item.get("is_spam", False),
        "is_duplicate": item.get("is_duplicate", False),
        "pii_redacted": item.get("pii_redacted", False),
        "relevant": item.get("relevant", True),
        "primary_theme": item.get("primary_theme"),
        "sentiment": item.get("sentiment"),
        "status": status,
        "filter_reason": item.get("filter_reason"),
    }


@router.get("/feed")
def feed(week: str | None = None, db: Session = Depends(get_db)):
    w = get_week(db, week)
    all_ingested = raw_for_week(db, w)
    scored = scored_for_week(db, w)
    coverage = coverage_for_run(db)

    scored_by_id = {s.id: s.model_dump(mode="json") for s in scored}

    spam = sum(1 for i in all_ingested if i.get("is_spam"))
    dupes = sum(1 for i in all_ingested if i.get("is_duplicate"))
    pii = sum(1 for i in all_ingested if i.get("pii_redacted"))
    translated = sum(1 for i in all_ingested if i.get("translated"))
    non_ctrl = sum(1 for s in scored if not s.relevant)
    active_count = sum(1 for s in scored if s.relevant)

    active_items = []
    for s in scored:
        if not s.relevant:
            continue
        d = scored_by_id[s.id]
        active_items.append(_item_card({**d, "filter_reason": None}, status="active"))

    filtered_items = []
    for i in all_ingested:
        if i.get("is_spam"):
            filtered_items.append(_item_card({**i, "filter_reason": "Spam review-bomb removed"}, status="filtered"))
        elif i.get("is_duplicate"):
            filtered_items.append(_item_card({**i, "filter_reason": "Duplicate text removed"}, status="filtered"))

    for s in scored:
        if not s.relevant:
            d = scored_by_id[s.id]
            filtered_items.append(
                _item_card({**d, "filter_reason": "Non-controllable topic (e.g. film choice)"}, status="filtered")
            )

    active_items.sort(key=lambda x: x.get("ts") or "", reverse=True)
    filtered_items.sort(key=lambda x: x.get("ts") or "", reverse=True)

    has_data = len(all_ingested) > 0 or len(scored) > 0

    return {
        "week": w,
        "has_data": has_data,
        "pipeline": {
            "total_received": len(all_ingested),
            "active_in_feed": active_count,
            "spam_removed": spam,
            "duplicates_removed": dupes,
            "non_controllable": non_ctrl,
            "pii_redacted": pii,
            "translated": translated,
        },
        "active_items": active_items,
        "filtered_items": filtered_items,
        "source_coverage": coverage.model_dump(mode="json"),
    }
