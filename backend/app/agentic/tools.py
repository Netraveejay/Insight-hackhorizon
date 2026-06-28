"""Read-only tools for reasoning agents — wrap deterministic queries."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents.retrieval import (
    RETRIEVAL_TOOLS,
    get_cluster,
    get_detections,
    get_language_mix,
    get_negative_feedback,
    get_positive_themes,
    get_root_cause,
    get_site,
    get_sla_status,
    get_theme_trend,
    get_top_issues,
    search_feedback,
)
from app.schemas import SITE_BY_ID
from app.services import clusters_for_week, detections_for_week, get_week, scored_for_week


def check_contagion(db: Session, theme: str, week: str | None = None) -> dict:
    """Is this theme issue spreading across sites or local to one?"""
    w = get_week(db, week)
    clusters = [c for c in clusters_for_week(db, w) if theme in c.theme and c.neg > 0]
    by_site: dict[str, int] = {}
    for c in clusters:
        by_site[c.site_id] = by_site.get(c.site_id, 0) + c.neg
    sites = [
        {
            "site_id": sid,
            "site_name": SITE_BY_ID.get(sid, {}).get("name", sid),
            "neg": neg,
        }
        for sid, neg in sorted(by_site.items(), key=lambda x: -x[1])
    ]
    return {
        "week": w,
        "theme": theme,
        "site_count": len(sites),
        "sites": sites[:8],
        "spreading": len(sites) > 1,
        "total_neg": sum(by_site.values()),
    }


def correlate_with_staff(db: Session, site_id: str, theme: str, week: str | None = None) -> dict:
    """Guest vs staff signal alignment for a site×theme."""
    w = get_week(db, week)
    scored = scored_for_week(db, w)
    guest_neg = staff_neg = 0
    for row in scored:
        if row.site_id != site_id:
            continue
        if theme not in (row.themes or []) and row.primary_theme != theme:
            continue
        sent = row.sentiment.get(row.primary_theme, "neutral")
        if sent != "negative":
            continue
        if row.source_type == "staff":
            staff_neg += 1
        else:
            guest_neg += 1
    detections = detections_for_week(db, w)
    cross = any(
        d.cross_source
        for d in detections
        if any(c.site_id == site_id and theme in c.theme for c in clusters_for_week(db, w) if c.cluster_id == d.cluster_id)
    )
    return {
        "week": w,
        "site_id": site_id,
        "site_name": SITE_BY_ID.get(site_id, {}).get("name", site_id),
        "theme": theme,
        "guest_neg": guest_neg,
        "staff_neg": staff_neg,
        "cross_source": cross,
        "aligned": guest_neg > 0 and staff_neg > 0,
    }


def compare_sites(db: Session, site_a: str, site_b: str, week: str | None = None) -> dict:
    w = get_week(db, week)
    return {
        "week": w,
        "site_a": get_site(db, site_a, w),
        "site_b": get_site(db, site_b, w),
    }


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_top_issues": {
        "description": "Week overview and ranked priority issues",
        "input_schema": {"week": "string"},
        "fn": get_top_issues,
        "agent": "detection",
    },
    "get_cluster": {
        "description": "Single cluster detail by cluster_id",
        "input_schema": {"cluster_id": "string", "week": "string"},
        "fn": get_cluster,
        "agent": "clustering",
    },
    "get_root_cause": {
        "description": "Root cause taxonomy for a cluster",
        "input_schema": {"cluster_id": "string", "week": "string"},
        "fn": get_root_cause,
        "agent": "root_cause",
    },
    "get_detections": {
        "description": "Detection flags (cross_source, compounding, spike)",
        "input_schema": {"week": "string", "kind": "string"},
        "fn": get_detections,
        "agent": "detection",
    },
    "get_site": {
        "description": "Top issues for one site",
        "input_schema": {"site_id": "string", "week": "string"},
        "fn": get_site,
        "agent": "clustering",
    },
    "get_theme_trend": {
        "description": "Theme volume trend across weeks",
        "input_schema": {"theme": "string"},
        "fn": get_theme_trend,
        "agent": "clustering",
    },
    "check_contagion": {
        "description": "Whether a theme issue is spreading across sites",
        "input_schema": {"theme": "string", "week": "string"},
        "fn": check_contagion,
        "agent": "detection",
    },
    "compare_sites": {
        "description": "Compare top issues at two sites",
        "input_schema": {"site_a": "string", "site_b": "string", "week": "string"},
        "fn": compare_sites,
        "agent": "clustering",
    },
    "get_sla_status": {
        "description": "SLA on_track / at_risk / breached counts",
        "input_schema": {"week": "string"},
        "fn": get_sla_status,
        "agent": "sla",
    },
    "get_language_mix": {
        "description": "Language distribution for the week",
        "input_schema": {"week": "string"},
        "fn": get_language_mix,
        "agent": "translation",
    },
    "get_positive_themes": {
        "description": "Strongest positive themes",
        "input_schema": {"week": "string"},
        "fn": get_positive_themes,
        "agent": "scoring",
    },
    "get_negative_feedback": {
        "description": "Ranked negative guest comment text",
        "input_schema": {"week": "string", "limit": "int", "site_id": "string", "theme": "string"},
        "fn": get_negative_feedback,
        "agent": "scoring",
    },
    "search_feedback": {
        "description": "Keyword search over feedback text",
        "input_schema": {"text": "string", "week": "string"},
        "fn": search_feedback,
        "agent": "ingestion",
    },
    "correlate_with_staff": {
        "description": "Guest vs staff negative signals for site×theme",
        "input_schema": {"site_id": "string", "theme": "string", "week": "string"},
        "fn": correlate_with_staff,
        "agent": "detection",
    },
}


def call_tool(db: Session, name: str, inputs: dict) -> dict:
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")
    fn: Callable = TOOL_REGISTRY[name]["fn"]
    schema = TOOL_REGISTRY[name]["input_schema"]
    clean = {k: inputs[k] for k in schema if k in inputs and inputs[k] is not None}
    return fn(db, **clean)


def tool_agent(name: str) -> str:
    return TOOL_REGISTRY.get(name, {}).get("agent", "coordinator")

# Re-export for tests
RETRIEVAL_TOOL_NAMES = set(RETRIEVAL_TOOLS.keys()) | {"check_contagion", "compare_sites", "correlate_with_staff"}
