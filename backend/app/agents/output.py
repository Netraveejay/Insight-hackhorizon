from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

import httpx

from app.config import get_settings
from app.models import AlertRow, DistributionLogRow
from app.schemas import (
    SITE_BY_ID,
    SITES,
    Cluster,
    Detection,
    Insight,
    LanguageStatsReport,
    ScoredItem,
    SourceCoverageReport,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OutputAgent:
    """Deterministic distribution — digests, reports, alerts. Internal targets only."""

    def render_overview(
        self,
        scored: list[ScoredItem],
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        week: str,
        language_stats: LanguageStatsReport | None = None,
    ) -> dict:
        csat_items = [s for s in scored if s.channel == "csat" and s.rating is not None]
        csat_pct = 0.0
        if csat_items:
            positive = sum(1 for s in csat_items if s.rating >= 4)
            csat_pct = round(100 * positive / len(csat_items), 1)

        det_map = {d.cluster_id: d for d in detections}
        ranked = []
        for c in sorted(clusters, key=lambda x: (-x.neg, x.cluster_id)):
            d = det_map.get(c.cluster_id)
            if d and d.priority:
                ins = next((i for i in insights if i.cluster_id == c.cluster_id), None)
                ranked.append(
                    {
                        "cluster_id": c.cluster_id,
                        "site_id": c.site_id,
                        "site_name": SITE_BY_ID.get(c.site_id, {}).get("name", c.site_id),
                        "theme": c.theme,
                        "priority": d.priority,
                        "neg": c.neg,
                        "insight": ins.insight if ins else None,
                        "flags": self._flags(d),
                        "root_cause_summary": (d.root_cause or {}).get("summary"),
                        "sla_status": (d.sla or {}).get("status"),
                        "sla_label": (d.sla or {}).get("label"),
                    }
                )
        ranked.sort(key=lambda x: ({"P1": 0, "P2": 1, "P3": 2}.get(x["priority"], 9), -x["neg"]))

        positive_themes: dict[str, int] = {}
        for s in scored:
            if s.sentiment.get(s.primary_theme) == "positive" and s.relevant:
                positive_themes[s.primary_theme] = positive_themes.get(s.primary_theme, 0) + 1

        hero = ranked[0] if ranked else None
        cross_source_count = sum(1 for d in detections if d.cross_source)

        priority_detections = [d for d in detections if d.priority]
        sla_summary = {
            "on_track": sum(1 for d in priority_detections if (d.sla or {}).get("status") == "on_track"),
            "at_risk": sum(1 for d in priority_detections if (d.sla or {}).get("status") == "at_risk"),
            "breached": sum(1 for d in priority_detections if (d.sla or {}).get("status") == "breached"),
        }

        language_mix = []
        if language_stats:
            language_mix = [
                {"language": ls.language, "count": ls.count, "translated": ls.translated_count}
                for ls in language_stats.languages[:6]
            ]
        elif scored:
            from collections import Counter
            langs = Counter(s.original_language for s in scored)
            language_mix = [{"language": k, "count": v, "translated": 0} for k, v in langs.most_common(6)]

        return {
            "week": week,
            "weighted_csat_pct": csat_pct,
            "open_issues": len([d for d in detections if d.priority]),
            "cross_source_flags": cross_source_count,
            "items_processed": len(scored),
            "ranked_actions": ranked[:10],
            "positive_themes": sorted(positive_themes.items(), key=lambda x: -x[1])[:5],
            "hero_issue": hero,
            "language_mix": language_mix,
            "sla_summary": sla_summary,
        }

    def render_feed(
        self,
        ingested_payload: list[dict],
        coverage: SourceCoverageReport,
        week: str,
    ) -> dict:
        spam = sum(1 for i in ingested_payload if i.get("is_spam"))
        dup = sum(1 for i in ingested_payload if i.get("is_duplicate"))
        non_ctrl = sum(1 for i in ingested_payload if not i.get("relevant", True))
        pii = sum(1 for i in ingested_payload if i.get("pii_redacted"))
        return {
            "week": week,
            "items": ingested_payload,
            "filters_summary": {
                "spam": spam,
                "duplicate": dup,
                "non_controllable": non_ctrl,
                "pii_redacted": pii,
                "translated": sum(1 for i in ingested_payload if i.get("translated")),
            },
            "source_coverage": coverage.model_dump(mode="json"),
        }

    def render_digest(
        self,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        scored: list[ScoredItem],
        coverage: SourceCoverageReport,
        week: str,
    ) -> dict:
        theme_totals: dict[str, dict] = {}
        for c in clusters:
            if c.theme not in theme_totals:
                theme_totals[c.theme] = {"volume": 0, "neg": 0, "pos": 0}
            theme_totals[c.theme]["volume"] += c.volume
            theme_totals[c.theme]["neg"] += c.neg
            theme_totals[c.theme]["pos"] += c.pos

        det_map = {d.cluster_id: d for d in detections}
        friction = [
            c for c in clusters if c.neg > 0 and det_map.get(c.cluster_id, Detection(cluster_id=c.cluster_id)).priority
        ]
        friction.sort(key=lambda x: -x.neg)

        site_table = []
        for site in SITES:
            site_clusters = [c for c in clusters if c.site_id == site["id"]]
            site_table.append(
                {
                    "site_id": site["id"],
                    "name": site["name"],
                    "total_volume": sum(c.volume for c in site_clusters),
                    "total_neg": sum(c.neg for c in site_clusters),
                    "top_theme": max(site_clusters, key=lambda c: c.neg).theme if site_clusters else None,
                }
            )

        return {
            "week": week,
            "title": f"Weekly Executive Digest — {week}",
            "national_theme_totals": theme_totals,
            "top_friction_clusters": [c.model_dump() for c in friction[:5]],
            "action_priorities": [
                {
                    "cluster_id": i.cluster_id,
                    "insight": i.insight,
                    "owner": i.owner_suggested,
                    "status": i.status,
                }
                for i in insights
                if det_map.get(i.cluster_id) and det_map[i.cluster_id].priority in ("P1", "P2")
            ],
            "positive_themes": self._positive_summary(scored),
            "per_site_table": site_table,
            "source_coverage": coverage.model_dump(mode="json"),
        }

    def render_summary(
        self,
        clusters: list[Cluster],
        detections: list[Detection],
        month: str,
    ) -> dict:
        month_clusters = [c for c in clusters if c.week.startswith(month[:4])]
        trajectories: dict[str, list] = {}
        for c in month_clusters:
            trajectories.setdefault(c.theme, []).append({"week": c.week, "neg": c.neg, "pos": c.pos})

        rising, falling, persistent = [], [], []
        for theme, series in trajectories.items():
            negs = [s["neg"] for s in sorted(series, key=lambda x: x["week"])]
            if len(negs) >= 2 and negs[-1] > negs[0]:
                rising.append(theme)
            elif len(negs) >= 2 and negs[-1] < negs[0]:
                falling.append(theme)
            elif sum(negs) >= 3:
                persistent.append(theme)

        return {
            "month": month,
            "headline_tiles": {
                "total_clusters": len(month_clusters),
                "total_negatives": sum(c.neg for c in month_clusters),
                "p1_count": sum(1 for d in detections if d.priority == "P1"),
                "sites_affected": len({c.site_id for c in month_clusters if c.neg > 0}),
            },
            "theme_trajectories": {"rising": rising, "falling": falling, "persistent": persistent},
            "site_concentration": self._site_concentration(month_clusters),
            "opportunities": [
                {"theme": t, "sites": len({c.site_id for c in month_clusters if c.theme == t and c.pos > c.neg})}
                for t in set(c.theme for c in month_clusters)
            ],
        }

    def render_site_report(
        self,
        site_id: str,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        scored: list[ScoredItem],
        week: str,
    ) -> dict:
        site = SITE_BY_ID.get(site_id, {"id": site_id, "name": site_id, "email": ""})
        site_clusters = [c for c in clusters if c.site_id == site_id and c.week == week]
        det_map = {d.cluster_id: d for d in detections}
        site_insights = {i.cluster_id: i for i in insights}

        return {
            "site": site,
            "week": week,
            "clusters": [
                {
                    **c.model_dump(),
                    "detection": det_map.get(c.cluster_id).model_dump() if det_map.get(c.cluster_id) else None,
                    "insight": site_insights[c.cluster_id].model_dump() if c.cluster_id in site_insights else None,
                }
                for c in site_clusters
            ],
            "feedback_count": len([s for s in scored if s.site_id == site_id and s.week == week]),
            "distribution_target": site["email"],
            "note": "Internal report only — not sent to guests",
        }

    def distribute(
        self,
        db: Session,
        run_id: str,
        week: str,
        clusters: list[Cluster],
        detections: list[Detection],
        insights: list[Insight],
        coverage: SourceCoverageReport,
        language_stats: LanguageStatsReport | None = None,
    ) -> list[AlertRow]:
        alerts: list[AlertRow] = []
        det_map = {d.cluster_id: d for d in detections}

        for d in detections:
            c = next((x for x in clusters if x.cluster_id == d.cluster_id), None)
            if not c:
                continue
            if d.spike:
                alerts.append(self._make_alert(run_id, week, "spike", c, d))
            if d.compounding:
                alerts.append(self._make_alert(run_id, week, "compounding", c, d))
            if d.cross_source:
                alerts.append(self._make_alert(run_id, week, "cross_source", c, d))

        # Per-site email fan-out (log only — internal)
        for site in SITES:
            log = DistributionLogRow(
                id=str(uuid.uuid4())[:16],
                run_id=run_id,
                target_type="email",
                target=site["email"],
                payload_summary=f"Weekly site report for {site['name']} — week {week}",
            )
            db.add(log)

        settings = get_settings()
        for alert in alerts:
            db.add(alert)
            if settings.teams_webhook_url:
                delivered = self._send_teams_webhook(settings.teams_webhook_url, alert)
                alert.payload = {**(alert.payload or {}), "teams_delivered": delivered}
                db.add(
                    DistributionLogRow(
                        id=str(uuid.uuid4())[:16],
                        run_id=run_id,
                        target_type="teams",
                        target=settings.teams_webhook_url[:80],
                        payload_summary=f"Teams alert: {alert.message[:120]}",
                    )
                )

        digest_log = DistributionLogRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            target_type="digest",
            target="executive@bcs.com.au",
            payload_summary=f"Weekly executive digest — week {week}",
        )
        db.add(digest_log)
        return alerts

    def create_disruption_alert(
        self, db: Session, run_id: str, week: str, site_id: str, text: str
    ) -> AlertRow:
        alert = AlertRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            week=week,
            alert_type="disruption",
            site_id=site_id,
            theme=None,
            message=f"Disruption notification at {site_id}: {text[:200]}",
            priority="P1",
            payload={"text": text},
        )
        db.add(alert)
        return alert

    def _make_alert(self, run_id: str, week: str, alert_type: str, cluster: Cluster, det: Detection) -> AlertRow:
        site_name = SITE_BY_ID.get(cluster.site_id, {}).get("name", cluster.site_id)
        theme_label = cluster.theme.replace("_", " ")
        sla_note = ""
        if det.sla and det.sla.get("label"):
            sla_note = f" · {det.sla['label']}"
        return AlertRow(
            id=str(uuid.uuid4())[:16],
            run_id=run_id,
            week=week,
            alert_type=alert_type,
            site_id=cluster.site_id,
            theme=cluster.theme,
            message=(
                f"{alert_type.replace('_', ' ').title()} at {site_name} — {theme_label} "
                f"({cluster.neg} negatives){sla_note}"
            ),
            priority=det.priority,
            payload=det.model_dump(mode="json"),
        )

    def _send_teams_webhook(self, url: str, alert: AlertRow) -> bool:
        try:
            resp = httpx.post(url, json={"text": alert.message}, timeout=5)
            return resp.is_success
        except Exception as e:
            logger.warning("Teams webhook failed: %s", e)
            return False

    def render_language_summary(self, stats: LanguageStatsReport) -> dict:
        return {
            "week": stats.week,
            "total_items": stats.total_items,
            "languages": [ls.model_dump() for ls in stats.languages],
        }

    def _flags(self, d: Detection) -> list[str]:
        flags = []
        if d.cross_source:
            flags.append("cross-source")
        if d.compounding:
            flags.append("compounding")
        if d.spike:
            flags.append("spike")
        return flags

    def _positive_summary(self, scored: list[ScoredItem]) -> list[dict]:
        counts: dict[str, int] = {}
        for s in scored:
            if s.sentiment.get(s.primary_theme) == "positive":
                counts[s.primary_theme] = counts.get(s.primary_theme, 0) + 1
        return [{"theme": t, "count": c} for t, c in sorted(counts.items(), key=lambda x: -x[1])[:5]]

    def _site_concentration(self, clusters: list[Cluster]) -> list[dict]:
        result = []
        for site in SITES:
            sc = [c for c in clusters if c.site_id == site["id"]]
            if sc:
                top = max(sc, key=lambda c: c.neg)
                result.append({"site_id": site["id"], "name": site["name"], "top_theme": top.theme, "neg": top.neg})
        return sorted(result, key=lambda x: -x["neg"])[:10]
