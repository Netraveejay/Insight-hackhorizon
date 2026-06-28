"""Theatre leaderboard — ranks operators by problem-solving efficiency."""

from __future__ import annotations

from app.schemas import SITE_BY_ID, THEATRES, Cluster, Detection, ScoredItem

_SLA_POINTS = {"on_track": 100.0, "at_risk": 55.0, "breached": 0.0}


def prior_week(week: str) -> str | None:
    if "-W" not in week:
        return None
    year, wpart = week.split("-W", 1)
    try:
        wnum = int(wpart)
    except ValueError:
        return None
    if wnum <= 1:
        return None
    return f"{year}-W{wnum - 1:02d}"


def _site_metrics(
    site_id: str,
    clusters: list[Cluster],
    prior_clusters: list[Cluster],
    detections: list[Detection],
    scored: list[ScoredItem],
) -> dict:
    det_map = {d.cluster_id: d for d in detections}
    site_clusters = [c for c in clusters if c.site_id == site_id]
    prior_site = [c for c in prior_clusters if c.site_id == site_id]

    priority_dets: list[Detection] = []
    for c in site_clusters:
        d = det_map.get(c.cluster_id)
        if d and d.priority:
            priority_dets.append(d)

    if priority_dets:
        sla_vals = [_SLA_POINTS.get((d.sla or {}).get("status", "on_track"), 50.0) for d in priority_dets]
        sla_compliance_pct = round(sum(sla_vals) / len(sla_vals), 1)
        handled = sum(1 for d in priority_dets if not d.compounding)
        issue_handling_pct = round(100 * handled / len(priority_dets), 1)
        open_p1 = sum(1 for d in priority_dets if d.priority == "P1")
        open_p2 = sum(1 for d in priority_dets if d.priority == "P2")
        severity_penalty = min(100.0, open_p1 * 25.0 + open_p2 * 12.0)
    else:
        sla_compliance_pct = 100.0
        issue_handling_pct = 100.0
        open_p1 = 0
        open_p2 = 0
        severity_penalty = 0.0

    severity_score = 100.0 - severity_penalty

    csat_items = [
        s for s in scored if s.site_id == site_id and s.channel == "csat" and s.rating is not None
    ]
    if csat_items:
        csat_pct = round(100 * sum(1 for s in csat_items if s.rating >= 4) / len(csat_items), 1)
    else:
        csat_pct = 75.0

    neg_now = sum(c.neg for c in site_clusters)
    neg_prior = sum(c.neg for c in prior_site)
    if neg_prior > 0:
        improvement_pct = round(100 * max(0, neg_prior - neg_now) / neg_prior, 1)
    elif neg_now == 0:
        improvement_pct = 100.0
    else:
        improvement_pct = 0.0

    efficiency_score = round(
        0.30 * sla_compliance_pct
        + 0.25 * issue_handling_pct
        + 0.20 * csat_pct
        + 0.15 * severity_score
        + 0.10 * improvement_pct,
        1,
    )

    site = SITE_BY_ID.get(site_id, {"id": site_id, "name": site_id})
    return {
        "site_id": site_id,
        "site_name": site["name"],
        "efficiency_score": efficiency_score,
        "sla_compliance_pct": sla_compliance_pct,
        "issue_handling_pct": issue_handling_pct,
        "csat_pct": csat_pct,
        "improvement_pct": improvement_pct,
        "open_p1": open_p1,
        "open_p2": open_p2,
        "open_issues": len(priority_dets),
    }


def build_leaderboard(
    week: str,
    clusters: list[Cluster],
    prior_clusters: list[Cluster],
    detections: list[Detection],
    scored: list[ScoredItem],
) -> dict:
    entries = []
    for theatre in THEATRES:
        site_metrics = [
            _site_metrics(sid, clusters, prior_clusters, detections, scored)
            for sid in theatre["site_ids"]
        ]
        n = len(site_metrics) or 1
        entry = {
            "theatre_id": theatre["id"],
            "theatre_name": theatre["name"],
            "region": theatre["region"],
            "site_count": len(theatre["site_ids"]),
            "sites": sorted(site_metrics, key=lambda s: -s["efficiency_score"]),
            "efficiency_score": round(sum(s["efficiency_score"] for s in site_metrics) / n, 1),
            "sla_compliance_pct": round(sum(s["sla_compliance_pct"] for s in site_metrics) / n, 1),
            "issue_handling_pct": round(sum(s["issue_handling_pct"] for s in site_metrics) / n, 1),
            "csat_pct": round(sum(s["csat_pct"] for s in site_metrics) / n, 1),
            "improvement_pct": round(sum(s["improvement_pct"] for s in site_metrics) / n, 1),
            "open_p1": sum(s["open_p1"] for s in site_metrics),
            "open_p2": sum(s["open_p2"] for s in site_metrics),
            "open_issues": sum(s["open_issues"] for s in site_metrics),
        }
        entries.append(entry)

    entries.sort(key=lambda e: (-e["efficiency_score"], e["theatre_name"]))
    for i, entry in enumerate(entries, start=1):
        entry["rank"] = i
        entry["badge"] = "top" if i == 1 else None

    return {
        "week": week,
        "prior_week": prior_week(week),
        "top_theatre_id": entries[0]["theatre_id"] if entries else None,
        "top_theatre_name": entries[0]["theatre_name"] if entries else None,
        "methodology": (
            "Efficiency score blends SLA compliance (30%), non-compounding issue resolution (25%), "
            "guest CSAT (20%), open-severity penalty (15%), and week-on-week negative trend (10%). "
            "Theatres are compared on the average across their sites — site counts differ by operator."
        ),
        "entries": entries,
        "total_theatres": len(entries),
        "total_sites": sum(e["site_count"] for e in entries),
    }
