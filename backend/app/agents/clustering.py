from __future__ import annotations

from collections import defaultdict

from app.rules import RulesConfig
from app.schemas import Cluster, ScoredItem


class ClusteringAgent:
    """Deterministic clustering by site × theme × week."""

    def run(self, items: list[ScoredItem], rules: RulesConfig) -> list[Cluster]:
        groups: dict[tuple[str, str, str], list[ScoredItem]] = defaultdict(list)
        for item in items:
            if not item.relevant:
                continue
            key = (item.site_id, item.primary_theme, item.week)
            groups[key].append(item)

        clusters: list[Cluster] = []
        for (site_id, theme, week), group in groups.items():
            neg = sum(1 for i in group if i.sentiment.get(i.primary_theme) == "negative")
            pos = sum(1 for i in group if i.sentiment.get(i.primary_theme) == "positive")
            net = sum(i.score for i in group)
            source_types = {i.source_type for i in group}
            if len(source_types) > 1:
                st: str = "mixed"
            elif "staff" in source_types:
                st = "staff"
            else:
                st = "guest"

            clusters.append(
                Cluster(
                    cluster_id=f"{site_id}__{theme}__{week}",
                    site_id=site_id,
                    theme=theme,
                    week=week,
                    volume=len(group),
                    neg=neg,
                    pos=pos,
                    net_sentiment=round(net, 4),
                    confidence_band=rules.confidence_band_for(len(group)),  # type: ignore[arg-type]
                    item_ids=[i.id for i in group],
                    source_type=st,  # type: ignore[arg-type]
                )
            )
        return clusters
