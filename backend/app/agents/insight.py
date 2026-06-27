from __future__ import annotations

import logging

from app.providers.insight_llm import get_insight_llm
from app.config import get_settings
from app.schemas import Cluster, Detection, Insight, ScoredItem

logger = logging.getLogger(__name__)


class InsightAgent:
    """The ONLY LLM agent — drafts recommendation text only."""

    def __init__(self):
        settings = get_settings()
        self.llm = get_insight_llm(settings.openai_api_key)

    def run(
        self,
        cluster: Cluster,
        detection: Detection | None,
        scored_items: list[ScoredItem],
        rules_version: str,
    ) -> Insight:
        sample_texts = [i.text for i in scored_items if i.id in cluster.item_ids][:5]
        insight = self.llm.draft(cluster, detection, sample_texts, rules_version)
        insight.evidence_sample = [i.id for i in scored_items if i.id in cluster.item_ids][:5]
        logger.info(
            "Insight drafted for %s via %s",
            cluster.cluster_id,
            insight.draft_source,
        )
        return insight
