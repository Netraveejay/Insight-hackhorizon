from __future__ import annotations

from app.rules import RulesConfig
from app.schemas import Cluster, Detection


class DetectionAgent:
    """Deterministic detection — spike, compounding, cross-source, priority."""

    def run(
        self,
        current_clusters: list[Cluster],
        historical_clusters: list[Cluster],
        staff_clusters: list[Cluster],
        rules: RulesConfig,
    ) -> list[Detection]:
        hist_by_key: dict[tuple[str, str, str], Cluster] = {
            (c.site_id, c.theme, c.week): c for c in historical_clusters
        }
        staff_keys = {(c.site_id, c.theme, c.week) for c in staff_clusters if c.neg > 0}
        staff_cluster_map = {(c.site_id, c.theme, c.week): c for c in staff_clusters}

        spike_min = rules.detection.get("spike_min_negatives", 4)
        compounding_weeks = rules.detection.get("compounding_weeks", 3)

        detections: list[Detection] = []
        for cluster in current_clusters:
            if cluster.neg == 0 and cluster.source_type != "staff":
                continue

            spike = self._detect_spike(cluster, hist_by_key, spike_min)
            compounding = self._detect_compounding(cluster, hist_by_key, compounding_weeks)
            cross_source = self._detect_cross_source(cluster, staff_keys, staff_cluster_map)
            priority = self._assign_priority(cluster, spike, compounding, cross_source)

            if spike or compounding or cross_source or priority:
                detections.append(
                    Detection(
                        cluster_id=cluster.cluster_id,
                        spike=spike,
                        compounding=compounding,
                        cross_source=cross_source,
                        priority=priority,
                    )
                )
        return detections

    def _prior_week(self, week: str) -> str:
        year, w = int(week[:4]), int(week.split("W")[1])
        w -= 1
        if w < 1:
            year -= 1
            w = 52
        return f"{year}-W{w:02d}"

    def _detect_spike(
        self, cluster: Cluster, hist: dict[tuple[str, str, str], Cluster], spike_min: int
    ) -> dict | None:
        if cluster.neg < spike_min:
            return None
        prior_week = self._prior_week(cluster.week)
        prior = hist.get((cluster.site_id, cluster.theme, prior_week))
        prior_neg = prior.neg if prior else 0
        if prior_neg == 0 and cluster.neg >= spike_min:
            return {"from": prior_neg, "to": cluster.neg}
        if prior_neg > 0 and cluster.neg >= 2 * prior_neg:
            return {"from": prior_neg, "to": cluster.neg}
        return None

    def _detect_compounding(
        self,
        cluster: Cluster,
        hist: dict[tuple[str, str, str], Cluster],
        required_weeks: int,
    ) -> dict | None:
        weeks_with_neg: list[str] = []
        year, w = int(cluster.week[:4]), int(cluster.week.split("W")[1])
        for offset in range(required_weeks):
            ww = w - offset
            yy = year
            if ww < 1:
                yy -= 1
                ww += 52
            week_str = f"{yy}-W{ww:02d}"
            c = hist.get((cluster.site_id, cluster.theme, week_str))
            if c and c.neg > 0:
                weeks_with_neg.append(week_str)
            elif week_str == cluster.week and cluster.neg > 0:
                weeks_with_neg.append(week_str)

        if cluster.neg > 0 and cluster.week not in weeks_with_neg:
            weeks_with_neg.append(cluster.week)

        if len(weeks_with_neg) >= required_weeks:
            first_seen = min(weeks_with_neg)
            return {"weeks": len(weeks_with_neg), "first_seen": first_seen}
        return None

    def _detect_cross_source(
        self,
        cluster: Cluster,
        staff_keys: set[tuple[str, str, str]],
        staff_map: dict[tuple[str, str, str], Cluster],
    ) -> dict | None:
        key = (cluster.site_id, cluster.theme, cluster.week)
        if cluster.source_type == "staff":
            return None
        if key in staff_keys:
            staff_ref = staff_map.get(key)
            return {
                "staff_ref": staff_ref.cluster_id if staff_ref else f"{cluster.site_id}__{cluster.theme}__{cluster.week}_staff",
                "staff_neg": staff_ref.neg if staff_ref else 1,
            }
        return None

    def _assign_priority(
        self,
        cluster: Cluster,
        spike: dict | None,
        compounding: dict | None,
        cross_source: dict | None,
    ) -> str | None:
        if compounding and cross_source:
            return "P1"
        if compounding or spike or (cluster.confidence_band == "high" and cluster.neg > 0):
            return "P2"
        if cluster.neg >= 3:
            return "P3"
        return None
