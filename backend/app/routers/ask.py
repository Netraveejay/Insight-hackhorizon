from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.output import OutputAgent
from app.db import get_db
from app.schemas import AskRequest, AskResponse, SITE_BY_ID
from app.services import clusters_for_week, detections_for_week, get_week, insights_for_week, scored_for_week

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, db: Session = Depends(get_db)):
    w = get_week(db, body.week)
    q = body.question.lower()
    clusters = clusters_for_week(db, w)
    detections = detections_for_week(db, w)
    insights = insights_for_week(db, w)
    scored = scored_for_week(db, w)
    det_map = {d.cluster_id: d for d in detections}

    references: list[str] = []

    # Cross-source intent
    if "cross" in q and "source" in q:
        xs = [d for d in detections if d.cross_source]
        if not xs:
            return AskResponse(answer="No cross-source matches found for this week.", references=[])
        parts = []
        for d in xs[:3]:
            c = next((x for x in clusters if x.cluster_id == d.cluster_id), None)
            if c:
                references.append(c.cluster_id)
                site = SITE_BY_ID.get(c.site_id, {}).get("name", c.site_id)
                parts.append(f"{site} {c.theme.replace('_', ' ')} (P{d.priority[-1]})")
        return AskResponse(
            answer=f"Cross-source flags this week: {'; '.join(parts)}.",
            references=references,
        )

    # Named site intent
    for site_id, site in SITE_BY_ID.items():
        if site_id.replace("_", " ") in q or site["name"].lower() in q:
            site_clusters = [c for c in clusters if c.site_id == site_id and c.neg > 0]
            site_clusters.sort(key=lambda c: -c.neg)
            if not site_clusters:
                return AskResponse(answer=f"No negative clusters for {site['name']} this week.", references=[])
            top = site_clusters[0]
            references.append(top.cluster_id)
            d = det_map.get(top.cluster_id)
            flags = []
            if d:
                if d.compounding:
                    flags.append("compounding")
                if d.cross_source:
                    flags.append("cross-source")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            return AskResponse(
                answer=f"Top issue at {site['name']}: {top.theme.replace('_', ' ')} with {top.neg} negatives{flag_str}.",
                references=references,
            )

    # Positive themes
    if "positive" in q:
        overview = OutputAgent().render_overview(scored, clusters, detections, insights, w)
        themes = overview.get("positive_themes", [])
        if not themes:
            return AskResponse(answer="No positive theme data for this week.", references=[])
        top = themes[0]
        return AskResponse(
            answer=f"Strongest positive theme: {top[0].replace('_', ' ')} with {top[1]} positive mentions.",
            references=[],
        )

    # Specific theme
    for theme in [
        "projection", "audio", "food", "cleanliness", "staff", "ticketing",
        "booking", "pricing", "seating", "accessibility",
    ]:
        if theme in q:
            theme_key = {
                "projection": "projection_quality",
                "audio": "audio_sound",
                "food": "f_and_b",
                "staff": "staff_service",
                "ticketing": "ticketing_queue",
                "booking": "booking_app",
                "pricing": "value_pricing",
                "seating": "comfort_seating",
            }.get(theme, theme)
            matching = [c for c in clusters if theme_key in c.theme and c.neg > 0]
            matching.sort(key=lambda c: -c.neg)
            if matching:
                top = matching[0]
                references.append(top.cluster_id)
                return AskResponse(
                    answer=f"Top {theme} complaint: {SITE_BY_ID.get(top.site_id, {}).get('name', top.site_id)} with {top.neg} negatives.",
                    references=references,
                )

    # Top complaints (default)
    if any(w in q for w in ["top", "complaint", "issue", "problem", "worst", "priority"]):
        overview = OutputAgent().render_overview(scored, clusters, detections, insights, w)
        hero = overview.get("hero_issue")
        if hero:
            references.append(hero["cluster_id"])
            return AskResponse(
                answer=(
                    f"Top priority: {hero['site_name']} — {hero['theme'].replace('_', ' ')} "
                    f"({hero['priority']}, {hero['neg']} negatives). "
                    f"{hero.get('insight', '')}"
                ),
                references=references,
            )
        ranked = overview.get("ranked_actions", [])
        if ranked:
            r = ranked[0]
            references.append(r["cluster_id"])
            return AskResponse(
                answer=f"Highest priority issue: {r['site_name']} {r['theme'].replace('_', ' ')} ({r['priority']}).",
                references=references,
            )

    # Daily briefing
    if "briefing" in q or "summary" in q or "brief" in q:
        overview = OutputAgent().render_overview(scored, clusters, detections, insights, w)
        return AskResponse(
            answer=(
                f"Week {w} briefing: {overview['items_processed']} items processed, "
                f"{overview['open_issues']} open issues, {overview['cross_source_flags']} cross-source flags. "
                f"Weighted CSAT {overview['weighted_csat_pct']}%. "
                + (
                    f"Hero issue: {overview['hero_issue']['site_name']} {overview['hero_issue']['theme'].replace('_', ' ')}."
                    if overview.get("hero_issue")
                    else "No P1 issues this week."
                )
            ),
            references=[overview["hero_issue"]["cluster_id"]] if overview.get("hero_issue") else [],
        )

    return AskResponse(
        answer="I can answer questions about top complaints, specific sites, cross-source flags, positive themes, language mix, or daily briefings. Try asking about Harbourview or cross-source issues.",
        references=[],
    )
